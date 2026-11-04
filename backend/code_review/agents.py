"""The AI reviewers: prompts, the (optional) tool-calling loop, and result validation.

Ported from the original AIP444 assignment. Differences: provider errors are translated into
typed `ReviewError`s, the loop works with tools switched off (the web API never exposes
filesystem tools), limits come from `Settings`, and findings carry more structure.
"""

import asyncio
import json
import logging
import os
import re
import time
from dataclasses import dataclass, field

import openai
from pydantic import ValidationError

from . import tools
from .config import Settings
from .diffs import ParsedDiff, parse_diff
from .errors import (
    InvalidCredentialsError,
    InvalidModelResponseError,
    ProviderError,
    ProviderUnavailableError,
    RateLimitedError,
    ReviewError,
)
from .redact import scrub
from .schemas import (
    REVIEWER_NAMES,
    TOOL_ARG_MODELS,
    TOOLS,
    CheckedFinding,
    Finding,
    ReviewerId,
    ReviewResult,
)

log = logging.getLogger("code_review.agents")

PROMPT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "prompts")

RESPONSE_FORMAT = {
    "type": "json_schema",
    "json_schema": {
        "name": "review_result",
        "strict": True,
        "schema": ReviewResult.model_json_schema(),
    },
}

TEMPERATURES: dict[ReviewerId, float] = {"security": 0.1, "maintainability": 0.3}
PROMPT_FILES: dict[ReviewerId, str] = {"security": "security.md", "maintainability": "maintainability.md"}

NO_TOOLS_SECTION = (
    "# Tools\n"
    "No tools are available in this session. Review ONLY the supplied code and do not make claims "
    "about files you cannot see. Where these rules mention verifying something with a tool, "
    "report only what the supplied code itself shows. Reply with the JSON object immediately."
)
_TOOLS_BLOCK = re.compile(r"<!-- tools:start -->.*?<!-- tools:end -->", re.DOTALL)


@dataclass(frozen=True)
class ReviewerSpec:
    id: ReviewerId
    model: str
    temperature: float
    prompt_file: str

    @property
    def name(self) -> str:
        return REVIEWER_NAMES[self.id]


def reviewer_spec(reviewer: ReviewerId, settings: Settings) -> ReviewerSpec:
    model = settings.security_model if reviewer == "security" else settings.maintainability_model
    return ReviewerSpec(reviewer, model, TEMPERATURES[reviewer], PROMPT_FILES[reviewer])


@dataclass
class UsageTotals:
    """Request and token counts for one reviewer (informational, shown in debug logs)."""

    requests: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    last_finish_reason: str | None = None

    def add(self, usage) -> None:
        self.requests += 1
        for attr in ("prompt_tokens", "completion_tokens"):
            value = getattr(usage, attr, None)
            if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
                setattr(self, attr, getattr(self, attr) + value)


@dataclass
class ReviewInput:
    mode: str  # "git" or "file"
    content: str  # the diff text, or the file contents
    paths: list[str]  # files included in the review (the only valid finding paths)
    diff: ParsedDiff | None = None  # Git mode only: line maps built from the diff

    def __post_init__(self):
        if self.mode == "git" and self.diff is None:
            self.diff = parse_diff(self.content)

    @property
    def line_count(self) -> int:
        return len(self.content.splitlines())


@dataclass
class ReviewerOutcome:
    id: ReviewerId
    model: str
    findings: list[CheckedFinding] = field(default_factory=list)
    error: ReviewError | None = None
    dropped: int = 0
    usage: UsageTotals | None = None


# ---------- Review input ----------


def check_line(review_input: ReviewInput, path: str, line: int | None) -> tuple[str, int | None]:
    """Verify a model-supplied line number. Returns (status, line to report)."""
    if line is None:
        return "none", None
    if review_input.mode != "git":
        # File mode: the line must exist in the file.
        return ("valid", line) if line <= review_input.line_count else ("unverified", None)
    file_diff = review_input.diff.files.get(path) if review_input.diff else None
    if file_diff is not None:
        if line in file_diff.added:
            return "added", line
        if line in file_diff.context:
            return "context", line
    return "unverified", None


def file_display_path(path: str) -> str:
    """Repo-relative path with forward slashes, or 'external:<path>' outside the repo."""
    real = os.path.realpath(path)
    root = os.path.normcase(tools.REPO_ROOT)
    try:
        inside = os.path.commonpath([root, os.path.normcase(real)]) == root
    except ValueError:  # different drives on Windows
        inside = False
    if inside:
        return os.path.relpath(real, tools.REPO_ROOT).replace("\\", "/")
    return "external:" + real.replace("\\", "/")


def _render_input(review_input: ReviewInput) -> tuple[str, str]:
    """Return (kind, section): the paths that may be cited, then the fenced code."""
    if review_input.mode == "git":
        kind = (
            "git diff of the staged changes. Each diff line is prefixed with its line number: "
            "'NEW n' = line n in the new version of the file (added or unchanged lines), "
            "'OLD n' = line n in the old version (removed lines)"
        )
        body = review_input.diff.rendered
    else:
        kind = "source file"
        lines = review_input.content.splitlines()
        width = len(str(len(lines)))
        body = "\n".join(f"{n:>{width}} | {line}" for n, line in enumerate(lines, start=1))

    # A fence longer than any backtick run in the code cannot be closed from inside it.
    fence = "```"
    while fence in body:
        fence += "`"

    path_lines = "\n".join(f"- {path}" for path in review_input.paths)
    note = ""
    if any(path.startswith("external:") for path in review_input.paths):
        note = (
            "\nNote: this file is outside the repository, so read_file and ripgrep "
            "cannot read it. Use the supplied code only.\n"
        )

    section = (
        f'Files included in this review (the only valid values for "path"):\n{path_lines}\n'
        f"{note}\n"
        f"<review-input>\n{fence}\n{body}\n{fence}\n</review-input>"
    )
    return kind, section


def build_user_prompt(review_input: ReviewInput, tools_enabled: bool) -> str:
    """Build the reviewers' user message: the paths that may be cited, then the fenced code."""
    kind, section = _render_input(review_input)
    closing = (
        "Use tools only if they will change your conclusion, then return the JSON object."
        if tools_enabled
        else "Return the JSON object."
    )
    return f"Review the following {kind}.\n\n{section}\n\n{closing}"


def load_prompt(spec: ReviewerSpec, tools_enabled: bool) -> str:
    try:
        with open(os.path.join(PROMPT_DIR, spec.prompt_file), encoding="utf-8") as file:
            text = file.read()
    except OSError as err:
        raise ProviderError(f"could not read prompt file {spec.prompt_file}: {err}") from err
    if tools_enabled:
        return text.replace("<!-- tools:start -->\n", "").replace("<!-- tools:end -->\n", "")
    return _TOOLS_BLOCK.sub(NO_TOOLS_SECTION, text)


# ---------- Model calls ----------


def _short_error(err: Exception) -> str:
    """A compact one-line description of a validation or JSON error."""
    if isinstance(err, ValidationError):
        parts = []
        for item in err.errors()[:3]:
            where = ".".join(str(p) for p in item["loc"]) or "response"
            parts.append(f"{where}: {item['msg']}")
        return "; ".join(parts)
    return str(err).splitlines()[0] if str(err) else type(err).__name__


def translate_api_error(err: Exception, secrets: tuple[str, ...] = ()) -> ReviewError:
    """Turn an OpenAI-SDK exception into a typed error whose message never contains a secret."""
    if isinstance(err, openai.AuthenticationError | openai.PermissionDeniedError):
        return InvalidCredentialsError("The AI provider rejected the API key. Check that it is valid.")
    if isinstance(err, openai.RateLimitError):
        return RateLimitedError("The AI provider rate limit was reached. Wait a moment and try again.")
    if isinstance(err, openai.APITimeoutError):
        return ProviderUnavailableError("The AI provider did not answer in time. Try again.")
    if isinstance(err, openai.APIConnectionError):
        return ProviderUnavailableError("Could not connect to the AI provider. Check your network.")
    if isinstance(err, openai.APIStatusError):
        message = scrub(getattr(err, "message", "") or "", secrets)[:200]
        if err.status_code >= 500:
            return ProviderUnavailableError(f"The AI provider had a server error (HTTP {err.status_code}).")
        return ProviderError(f"The AI provider rejected the request (HTTP {err.status_code}): {message}")
    return ProviderError(f"AI provider call failed: {type(err).__name__}")


async def _chat(
    client,
    spec: ReviewerSpec,
    messages: list[dict],
    *,
    use_tools: bool,
    totals: UsageTotals,
    settings: Settings,
    secrets: tuple[str, ...],
    tool_choice: str | None = None,
):
    """Send one chat request, record its usage in `totals`, and return the assistant message."""
    kwargs = {
        "model": spec.model,
        "messages": messages,
        "temperature": spec.temperature,
        "max_tokens": settings.max_tokens,
        "response_format": RESPONSE_FORMAT,
    }
    if use_tools:
        kwargs["tools"] = TOOLS
        if tool_choice is not None:  # never sent without tools: the API would reject it
            kwargs["tool_choice"] = tool_choice

    log.debug(
        "[%s] Request: model=%s, messages=%d, tools=%s",
        spec.id, spec.model, len(messages), "yes" if use_tools else "no",
    )  # fmt: skip
    try:
        try:
            response = await client.chat.completions.create(**kwargs)
        except (openai.BadRequestError, openai.UnprocessableEntityError):
            if kwargs.get("tool_choice") != "required":
                raise
            # The provider refused the forced tool call (a rejected request is not billed).
            # Retry this one request with "auto" rather than failing the whole review.
            log.warning("[%s] The provider rejected tool_choice='required'; retrying with 'auto'.", spec.id)
            kwargs["tool_choice"] = "auto"
            response = await client.chat.completions.create(**kwargs)
    except openai.OpenAIError as err:
        raise translate_api_error(err, secrets) from None

    choices = getattr(response, "choices", None)
    if not choices:
        raise InvalidModelResponseError("The AI provider returned an empty response.")

    totals.add(getattr(response, "usage", None))
    totals.last_finish_reason = choices[0].finish_reason
    log.debug("[%s] Response: finish_reason=%s", spec.id, choices[0].finish_reason)
    return choices[0].message


def _assistant_dict(message) -> dict:
    """Rebuild an assistant message that requested tools, in plain request format."""
    return {
        "role": "assistant",
        "content": message.content,
        "tool_calls": [
            {
                "id": call.id,
                "type": "function",
                "function": {"name": call.function.name, "arguments": call.function.arguments},
            }
            for call in message.tool_calls
        ],
    }


# ---------- Tools (CLI only) ----------


async def _execute_tool(reviewer: str, call, allowed: set[str]) -> str:
    """Run one requested tool call and return the result text. Never raises."""
    name = call.function.name
    arguments = call.function.arguments or ""

    model = TOOL_ARG_MODELS.get(name) if name in allowed else None
    if model is None:
        log.debug("[%s] Model requested unknown tool '%s'; not executed", reviewer, name)
        names = " and ".join(sorted(allowed))
        return f"ERROR: unknown tool '{name}'. Only {names} {'is' if len(allowed) == 1 else 'are'} available."

    try:
        args = model.model_validate_json(arguments)
    except ValidationError as err:
        return f"ERROR: invalid arguments for {name}: {_short_error(err)}"

    log.debug("[%s] Calling %s", reviewer, name)
    try:
        return await asyncio.to_thread(getattr(tools, name), **args.model_dump())
    except Exception as err:
        return f"ERROR: {name} failed: {type(err).__name__}: {err}"


def limit_tool_result(result: str, max_chars: int) -> str:
    """Cap what is sent to the model for any tool response (results and errors alike)."""
    if len(result) <= max_chars:
        return result
    note = (
        f"\n--- Tool output truncated to {max_chars} characters. "
        "Request a narrower line range or a more specific pattern."
    )
    return result[: max(max_chars - len(note), 0)] + note


async def _answer_tool_calls(reviewer: str, messages: list[dict], calls, settings: Settings) -> None:
    """Run the requested tools (concurrently) and append one tool message per call."""
    allowed = set(TOOL_ARG_MODELS)

    async def run(index: int, call) -> str:
        if index >= settings.max_calls_per_round:
            return f"ERROR: too many tool calls in one round (limit {settings.max_calls_per_round}); not executed."
        return await _execute_tool(reviewer, call, allowed)

    results = await asyncio.gather(*(run(i, call) for i, call in enumerate(calls)))
    for call, result in zip(calls, results, strict=True):
        messages.append(
            {"role": "tool", "tool_call_id": call.id, "content": limit_tool_result(result, settings.tool_max_chars)}
        )


# ---------- Results ----------


def parse_result(text: str | None) -> ReviewResult:
    """Parse a reviewer's reply text into a ReviewResult (raises on bad output)."""
    if not isinstance(text, str) or not text.strip():
        raise ValueError("the reply was empty")
    text = text.strip()
    fenced = re.match(r"^```(?:json)?\s*(.*?)\s*```$", text, re.DOTALL)
    if fenced:
        text = fenced.group(1)
    return ReviewResult.model_validate_json(text)


def match_allowed_path(path: str, allowed: set[str], renames: dict[str, str] | None = None) -> str | None:
    """Return the allowed path a finding refers to, or None for an invented path."""
    renames = renames or {}
    candidates = [path]
    if path.startswith(("a/", "b/")):
        candidates.append(path[2:])
    for candidate in candidates:
        if candidate in allowed:
            return candidate
        if candidate in renames:  # the file's old name, before a rename
            return renames[candidate]
    for item in allowed:
        if item.startswith("external:") and item[len("external:") :] == path:
            return item
    return None


def clean_findings(
    reviewer: str, findings: list[Finding], review_input: ReviewInput
) -> tuple[list[CheckedFinding], int]:
    """Drop findings for files not in the review, verify lines, and remove duplicates."""
    allowed = set(review_input.paths)
    renames = review_input.diff.renames if review_input.diff else {}
    kept: list[CheckedFinding] = []
    seen: set[tuple] = set()
    dropped = 0
    for finding in findings:
        path = match_allowed_path(finding.path, allowed, renames)
        if path is None:
            dropped += 1
            log.warning(
                "[%s] Dropped a finding for '%s': that file is not part of this review.", reviewer, finding.path
            )
            continue

        status, line = check_line(review_input, path, finding.line)
        claimed = None
        if status == "unverified":
            claimed = finding.line
            log.warning("[%s] Line %s for '%s' is not valid; reporting without a line number.", reviewer, claimed, path)

        key = (path, line, finding.category, finding.title.lower())
        if key in seen:
            continue
        seen.add(key)
        data = finding.model_dump()
        data.update(path=path, line=line)
        kept.append(CheckedFinding(**data, line_status=status, claimed_line=claimed))
    return kept, dropped


async def _final_result(client, spec, messages, message, totals, settings, secrets) -> ReviewResult:
    """Parse the final reply; on bad output, ask once more with the error."""
    try:
        return parse_result(message.content)
    except (ValueError, ValidationError) as err:
        problem = _short_error(err)
        log.debug("[%s] Malformed reply (%s); asking once more", spec.id, problem)
        messages.append({"role": "assistant", "content": message.content or ""})
        messages.append(
            {
                "role": "user",
                "content": f"Your reply was not valid ({problem}). Reply again with ONLY the JSON "
                'object {"findings": [...]} in the required format.',
            }
        )

    retry = await _chat(client, spec, messages, use_tools=False, totals=totals, settings=settings, secrets=secrets)
    try:
        return parse_result(retry.content)
    except (ValueError, ValidationError) as err:
        raise InvalidModelResponseError(
            f"The AI model returned malformed output twice ({_short_error(err)})."
        ) from None


async def _tool_loop(client, spec, messages, totals, settings, secrets):
    """Let the model call tools for a bounded number of rounds; return its final message.

    Round 1 forces a tool call (tool_choice='required'); later rounds use 'auto' so the model
    may answer.
    """
    for round_number in range(1, settings.max_tool_rounds + 1):
        choice = "required" if round_number == 1 else "auto"
        message = await _chat(
            client, spec, messages, use_tools=True, totals=totals, settings=settings,
            secrets=secrets, tool_choice=choice,
        )  # fmt: skip
        calls = message.tool_calls or []
        if not calls:
            return message
        log.debug("[%s] Round %d/%d: %d tool call(s)", spec.id, round_number, settings.max_tool_rounds, len(calls))
        messages.append(_assistant_dict(message))
        await _answer_tool_calls(spec.id, messages, calls, settings)

    log.debug("[%s] Tool round limit reached; requesting final answer", spec.id)
    messages.append(
        {
            "role": "user",
            "content": "The tool-call limit has been reached. Return the final JSON object now, "
            "using only the evidence gathered so far.",
        }
    )
    return await _chat(client, spec, messages, use_tools=False, totals=totals, settings=settings, secrets=secrets)


async def _review(client, spec, review_input, totals, settings, tools_enabled, secrets):
    messages = [
        {"role": "system", "content": load_prompt(spec, tools_enabled)},
        {"role": "user", "content": build_user_prompt(review_input, tools_enabled)},
    ]
    if tools_enabled:
        final = await _tool_loop(client, spec, messages, totals, settings, secrets)
    else:
        final = await _chat(client, spec, messages, use_tools=False, totals=totals, settings=settings, secrets=secrets)
    result = await _final_result(client, spec, messages, final, totals, settings, secrets)
    return clean_findings(spec.id, result.findings, review_input)


async def run_reviewer(
    client,
    spec: ReviewerSpec,
    review_input: ReviewInput,
    settings: Settings,
    *,
    tools_enabled: bool,
    secrets: tuple[str, ...] = (),
) -> ReviewerOutcome:
    """Run one reviewer to completion. Never raises; failures are in the outcome."""
    started = time.monotonic()
    totals = UsageTotals()
    log.debug("[%s] Reviewer starting (model=%s, tools=%s)", spec.id, spec.model, tools_enabled)
    try:
        findings, dropped = await _review(client, spec, review_input, totals, settings, tools_enabled, secrets)
    except ReviewError as err:
        log.debug("[%s] Reviewer failed: %s", spec.id, err.message)
        return ReviewerOutcome(spec.id, spec.model, error=err, usage=totals)
    except Exception as err:  # never let one reviewer's bug take down the other
        log.exception("[%s] Unexpected reviewer failure", spec.id)
        error = ReviewError(f"Unexpected {type(err).__name__} while running this reviewer.")
        return ReviewerOutcome(spec.id, spec.model, error=error, usage=totals)

    log.debug(
        "[%s] Finished in %.1fs: %d finding(s); tokens in/out %d/%d",
        spec.id, time.monotonic() - started, len(findings), totals.prompt_tokens, totals.completion_tokens,
    )  # fmt: skip
    return ReviewerOutcome(spec.id, spec.model, findings, dropped=dropped, usage=totals)


async def run_reviewers(
    client,
    review_input: ReviewInput,
    settings: Settings,
    reviewers: list[ReviewerId],
    *,
    tools_enabled: bool,
    secrets: tuple[str, ...] = (),
) -> list[ReviewerOutcome]:
    """Run the chosen reviewers at the same time and return their outcomes in order."""
    specs = [reviewer_spec(r, settings) for r in reviewers]
    return list(
        await asyncio.gather(
            *(
                run_reviewer(client, s, review_input, settings, tools_enabled=tools_enabled, secrets=secrets)
                for s in specs
            )
        )
    )


def describe_findings(outcomes: list[ReviewerOutcome]) -> str:
    """One-line summary used in debug logs."""
    return json.dumps({o.id: len(o.findings) for o in outcomes})
