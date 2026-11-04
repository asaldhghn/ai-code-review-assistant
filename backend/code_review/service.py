"""Review orchestration: validate input, pick demo or live engine, run the reviewers, and
assemble one `ReviewResponse`. Used by both the HTTP API and the CLI."""

import asyncio
import logging
import uuid
from collections.abc import Callable
from datetime import UTC, datetime

from .agents import ReviewerOutcome, ReviewInput, run_reviewers
from .config import Settings
from .demo import DEMO_ENGINE, run_demo_reviewer
from .errors import (
    InvalidInputError,
    LiveReviewDisabledError,
    MissingCredentialsError,
    PayloadTooLargeError,
    ProviderUnavailableError,
    ReviewError,
)
from .providers import create_client
from .schemas import (
    LANGUAGE_EXTENSIONS,
    REVIEWER_NAMES,
    ApiFinding,
    CheckedFinding,
    ReviewerCounts,
    ReviewerId,
    ReviewerStatus,
    ReviewMode,
    ReviewRequest,
    ReviewResponse,
    ReviewSummary,
    SeverityCounts,
)

log = logging.getLogger("code_review.service")

DEMO_NOTICE = (
    "Demo mode: these findings come from a deterministic rule-based scanner, not from an AI model. "
    "Switch to Live AI and add an API key for a real AI review."
)
MAX_KEY_LENGTH = 300
# If every reviewer fails, surface the most actionable error first.
_ERROR_PRIORITY = ("invalid_credentials", "rate_limited", "provider_unavailable", "invalid_response")

ClientFactory = Callable[[Settings, str], object]


def validate_code(code: str, settings: Settings) -> str:
    """Return the code if it is reviewable, otherwise raise a user-facing error."""
    if not code or not code.strip():
        raise InvalidInputError("There is no code to review. Paste some code first.", code="empty_code")
    if "\x00" in code:
        raise InvalidInputError(
            "The input looks like a binary file; only text source code can be reviewed.", code="binary_input"
        )
    if len(code) > settings.max_code_chars:
        raise PayloadTooLargeError(
            f"The code is {len(code):,} characters; the limit is {settings.max_code_chars:,}. Review a smaller file or section."
        )
    return code


def validate_api_key(key: str | None) -> str | None:
    if key is None:
        return None
    key = key.strip()
    if not key:
        return None
    if len(key) > MAX_KEY_LENGTH or any(ch.isspace() or not ch.isprintable() for ch in key):
        raise InvalidInputError("The API key has an invalid format.", code="invalid_api_key_format")
    return key


def snippet_path(request: ReviewRequest) -> str:
    return request.filename or f"snippet.{LANGUAGE_EXTENSIONS[request.language]}"


def _pick_error(outcomes: list[ReviewerOutcome]) -> ReviewError:
    errors = [o.error for o in outcomes if o.error is not None]
    for code in _ERROR_PRIORITY:
        for error in errors:
            if error.code == code:
                return error
    return errors[0]


def assemble_response(
    outcomes: list[ReviewerOutcome],
    *,
    mode: ReviewMode,
    language: str,
    filename: str,
    line_count: int,
    notices: list[str] | None = None,
    engine_labels: dict[str, str] | None = None,
) -> ReviewResponse:
    """Turn reviewer outcomes into the public response (ids, counts, statuses)."""
    findings: list[ApiFinding] = []
    statuses: list[ReviewerStatus] = []
    severity = SeverityCounts()
    by_reviewer = ReviewerCounts()
    notes = list(notices or [])

    for outcome in outcomes:
        prefix = outcome.id[0].upper()
        for number, finding in enumerate(outcome.findings, start=1):
            findings.append(_api_finding(f"{prefix}{number}", outcome.id, finding))
            setattr(severity, finding.severity, getattr(severity, finding.severity) + 1)
        setattr(by_reviewer, outcome.id, len(outcome.findings))
        if outcome.dropped:
            notes.append(
                f"{REVIEWER_NAMES[outcome.id]}: {outcome.dropped} finding(s) were discarded because they referred to files outside this review."
            )
        unverified = sum(1 for f in outcome.findings if f.line_status == "unverified")
        if unverified:
            notes.append(
                f"{REVIEWER_NAMES[outcome.id]}: {unverified} finding(s) are shown without a line number because the model's line could not be verified."
            )
        statuses.append(
            ReviewerStatus(
                id=outcome.id,
                name=REVIEWER_NAMES[outcome.id],
                status="failed" if outcome.error else "ok",
                engine=(engine_labels or {}).get(outcome.id, outcome.model),
                finding_count=len(outcome.findings),
                error_code=outcome.error.code if outcome.error else None,
                error_message=outcome.error.message if outcome.error else None,
            )
        )

    failed = [s for s in statuses if s.status == "failed"]
    for status in failed:
        notes.append(f"{status.name} could not complete: {status.error_message}")

    return ReviewResponse(
        review_id=uuid.uuid4().hex[:12],
        mode=mode,
        is_demo=mode == "demo",
        status="partial" if failed else "complete",
        created_at=datetime.now(UTC),
        language=language,
        filename=filename,
        line_count=line_count,
        summary=ReviewSummary(total=len(findings), by_severity=severity, by_reviewer=by_reviewer),
        reviewers=statuses,
        findings=findings,
        notices=notes,
    )


def _api_finding(finding_id: str, reviewer: ReviewerId, finding: CheckedFinding) -> ApiFinding:
    return ApiFinding(
        id=finding_id,
        reviewer=reviewer,
        title=finding.title,
        severity=finding.severity,
        category=finding.category,
        path=finding.path,
        line=finding.line,
        description=finding.description,
        why_it_matters=finding.why_it_matters,
        suggestion=finding.suggestion,
    )


def _demo_outcomes(request: ReviewRequest, code: str, path: str) -> list[ReviewerOutcome]:
    return [
        ReviewerOutcome(
            id=reviewer,
            model=DEMO_ENGINE,
            findings=[
                CheckedFinding(**f.model_dump(), line_status="valid" if f.line else "none")
                for f in run_demo_reviewer(reviewer, code, request.language, path)
            ],
        )
        for reviewer in request.reviewers
    ]


async def run_review(
    request: ReviewRequest,
    settings: Settings,
    *,
    api_key: str | None = None,
    client_factory: ClientFactory = create_client,
) -> ReviewResponse:
    """Run a review for the web API. Raises ReviewError subclasses for anything the user can fix."""
    code = validate_code(request.code, settings)
    path = snippet_path(request)
    line_count = len(code.splitlines())

    if request.mode == "demo":
        outcomes = _demo_outcomes(request, code, path)
        return assemble_response(
            outcomes, mode="demo", language=request.language, filename=path, line_count=line_count,
            notices=[DEMO_NOTICE], engine_labels={o.id: DEMO_ENGINE for o in outcomes},
        )  # fmt: skip

    if not settings.enable_live_review:
        raise LiveReviewDisabledError(
            "Live AI reviews are disabled on this server (demo-only deployment). Run the project locally with your own API key to use them."
        )
    key = validate_api_key(api_key) or settings.api_key
    if not key:
        raise MissingCredentialsError(
            "No API key available. Enter your key in the app, or set LLM_API_KEY / OPENROUTER_API_KEY on the server."
        )

    review_input = ReviewInput("file", code, [path])
    client = client_factory(settings, key)
    try:
        outcomes = await asyncio.wait_for(
            run_reviewers(client, review_input, settings, request.reviewers, tools_enabled=False, secrets=(key,)),
            timeout=settings.request_timeout_seconds,
        )
    except TimeoutError:
        raise ProviderUnavailableError("The review took too long and was cancelled. Try a smaller file.") from None
    finally:
        close = getattr(client, "close", None)
        if close is not None:
            await close()

    if all(o.error for o in outcomes):
        raise _pick_error(outcomes)
    return assemble_response(outcomes, mode="live", language=request.language, filename=path, line_count=line_count)
