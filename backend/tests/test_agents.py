import json

import openai
import pytest

from code_review import tools
from code_review.agents import (
    ReviewInput,
    clean_findings,
    limit_tool_result,
    load_prompt,
    match_allowed_path,
    parse_result,
    reviewer_spec,
    run_reviewer,
    run_reviewers,
    translate_api_error,
)
from code_review.config import Settings
from code_review.errors import (
    InvalidCredentialsError,
    InvalidModelResponseError,
    ProviderUnavailableError,
    RateLimitedError,
)
from code_review.schemas import Finding

from .fakes import FakeClient, connection_error, finding, message, reply, status_error, tool_call

SETTINGS = Settings()
CODE = 'import os\napi_key = "sk-live-abcdef123456"\n'
INPUT = ReviewInput("file", CODE, ["snippet.py"])


async def run(client, tools_enabled=False, reviewer="security"):
    return await run_reviewer(
        client,
        reviewer_spec(reviewer, SETTINGS),
        INPUT,
        SETTINGS,
        tools_enabled=tools_enabled,
        secrets=("sk-live-abcdef123456",),
    )


# ---------- parsing and cleaning ----------


def test_parse_result_accepts_fenced_json():
    text = "```json\n" + reply(finding()) + "\n```"
    assert len(parse_result(text).findings) == 1


@pytest.mark.parametrize("bad", [None, "", "   ", "not json", '{"findings": [{"path": "x"}]}', '{"other": 1}'])
def test_parse_result_rejects_bad_output(bad):
    with pytest.raises(ValueError):  # pydantic's ValidationError is a ValueError
        parse_result(bad)


def test_match_allowed_path_handles_prefixes_renames_and_invented_paths():
    allowed = {"src/a.py", "external:/tmp/x.py"}
    assert match_allowed_path("b/src/a.py", allowed) == "src/a.py"
    assert match_allowed_path("old.py", allowed, {"old.py": "src/a.py"}) == "src/a.py"
    assert match_allowed_path("/tmp/x.py", allowed) == "external:/tmp/x.py"
    assert match_allowed_path("invented.py", allowed) is None


def test_clean_findings_drops_foreign_paths_invalid_lines_and_duplicates():
    findings = [
        Finding(**finding()),
        Finding(**finding()),  # duplicate
        Finding(**finding(path="other.py")),  # not part of the review
        Finding(**finding(title="Out of range", line=999)),
    ]
    kept, dropped = clean_findings("security", findings, INPUT)
    assert dropped == 1
    assert [f.title for f in kept] == ["Hardcoded secret", "Out of range"]
    assert kept[1].line is None and kept[1].claimed_line == 999 and kept[1].line_status == "unverified"


def test_limit_tool_result_truncates_with_a_note():
    out = limit_tool_result("x" * 1000, 300)
    assert len(out) <= 300 and "truncated" in out
    assert limit_tool_result("short", 300) == "short"


# ---------- prompts ----------


def test_prompt_without_tools_has_no_tool_instructions():
    for reviewer in ("security", "maintainability"):
        text = load_prompt(reviewer_spec(reviewer, SETTINGS), tools_enabled=False)
        assert "No tools are available" in text
        assert "read_file(" not in text and "tools:start" not in text


def test_prompt_with_tools_keeps_tool_instructions_and_drops_markers():
    text = load_prompt(reviewer_spec("security", SETTINGS), tools_enabled=True)
    assert "ripgrep(search_pattern)" in text and "tools:start" not in text


def test_prompts_treat_code_as_untrusted_data():
    for reviewer in ("security", "maintainability"):
        assert "UNTRUSTED DATA" in load_prompt(reviewer_spec(reviewer, SETTINGS), tools_enabled=False)


# ---------- error translation ----------


def test_translate_api_errors_to_typed_errors():
    assert isinstance(translate_api_error(status_error(openai.AuthenticationError, 401)), InvalidCredentialsError)
    assert isinstance(translate_api_error(status_error(openai.RateLimitError, 429)), RateLimitedError)
    assert isinstance(translate_api_error(status_error(openai.InternalServerError, 503)), ProviderUnavailableError)
    assert isinstance(translate_api_error(connection_error()), ProviderUnavailableError)


def test_translated_messages_never_contain_the_api_key():
    secret = "sk-live-abcdef123456"
    err = translate_api_error(status_error(openai.BadRequestError, 400, f"bad key {secret}"), (secret,))
    assert secret not in err.message


# ---------- running a reviewer against a fake client ----------


async def test_reviewer_returns_validated_findings():
    client = FakeClient([reply(finding())])
    outcome = await run(client)
    assert outcome.error is None
    assert [f.title for f in outcome.findings] == ["Hardcoded secret"]
    assert outcome.findings[0].line_status == "valid"
    # No tools were offered, and the system prompt is the no-tools variant.
    call = client.calls[0]
    assert "tools" not in call and "tool_choice" not in call
    assert call["response_format"]["json_schema"]["strict"] is True
    assert "No tools are available" in call["messages"][0]["content"]


async def test_reviewer_retries_once_after_malformed_output():
    client = FakeClient(["this is not json", reply(finding())])
    outcome = await run(client)
    assert outcome.error is None and len(outcome.findings) == 1
    assert len(client.calls) == 2
    assert "not valid" in client.calls[1]["messages"][-1]["content"]


async def test_reviewer_fails_cleanly_after_two_malformed_replies():
    outcome = await run(FakeClient(["nope", "still nope"]))
    assert isinstance(outcome.error, InvalidModelResponseError)
    assert outcome.findings == []


@pytest.mark.parametrize(
    ("exc", "code"),
    [
        (status_error(openai.AuthenticationError, 401), "invalid_credentials"),
        (status_error(openai.RateLimitError, 429), "rate_limited"),
        (connection_error(), "provider_unavailable"),
        (status_error(openai.InternalServerError, 500), "provider_unavailable"),
    ],
)
async def test_provider_failures_become_typed_outcomes(exc, code):
    outcome = await run(FakeClient([exc]))
    assert outcome.error.code == code


async def test_unexpected_exceptions_are_contained():
    outcome = await run(FakeClient([RuntimeError("secret sk-live-abcdef123456 leaked")]))
    assert outcome.error is not None
    assert "sk-live" not in outcome.error.message


async def test_one_reviewer_failing_does_not_affect_the_other():
    class Split(FakeClient):
        async def _create(self, **kwargs):
            if "Security Auditor" in kwargs["messages"][0]["content"]:
                raise status_error(openai.RateLimitError, 429)
            return message(reply(finding(category="naming")))

    outcomes = await run_reviewers(Split(), INPUT, SETTINGS, ["security", "maintainability"], tools_enabled=False)
    assert outcomes[0].error.code == "rate_limited"
    assert outcomes[1].error is None and len(outcomes[1].findings) == 1


# ---------- tool loop (CLI mode) ----------


async def test_tool_loop_forces_first_call_executes_tool_and_returns_findings(tmp_path, monkeypatch):
    (tmp_path / "helper.py").write_text("def helper():\n    return 1\n", encoding="utf-8")
    monkeypatch.setattr(tools, "REPO_ROOT", str(tmp_path.resolve()))
    call = tool_call("read_file", {"file_path": "helper.py", "start_line": None, "end_line": None})
    client = FakeClient([message(None, [call], "tool_calls"), reply(finding())])
    outcome = await run(client, tools_enabled=True)

    assert outcome.error is None and len(outcome.findings) == 1
    assert client.calls[0]["tool_choice"] == "required"
    assert client.calls[1]["tool_choice"] == "auto"
    tool_message = next(m for m in client.calls[1]["messages"] if m["role"] == "tool")
    assert "def helper" in tool_message["content"]


async def test_tool_choice_required_falls_back_to_auto_when_provider_rejects_it():
    client = FakeClient([status_error(openai.BadRequestError, 400, "no required"), reply(finding())])
    outcome = await run(client, tools_enabled=True)
    assert outcome.error is None
    assert [c["tool_choice"] for c in client.calls] == ["required", "auto"]


async def test_model_cannot_call_unknown_tools(tmp_path, monkeypatch):
    monkeypatch.setattr(tools, "REPO_ROOT", str(tmp_path.resolve()))
    call = tool_call("run_shell", {"cmd": "rm -rf /"})
    client = FakeClient([message(None, [call], "tool_calls"), reply()])
    outcome = await run(client, tools_enabled=True)
    assert outcome.error is None
    tool_message = next(m for m in client.calls[1]["messages"] if m["role"] == "tool")
    assert "unknown tool" in tool_message["content"]


async def test_tool_rounds_are_bounded():
    settings = Settings(max_tool_rounds=2)
    call = tool_call("ripgrep", {"search_pattern": "zzz"})
    looping = message(None, [call], "tool_calls")
    client = FakeClient([looping, looping, reply()])
    outcome = await run_reviewer(client, reviewer_spec("security", settings), INPUT, settings, tools_enabled=True)
    assert outcome.error is None
    assert len(client.calls) == 3  # 2 tool rounds + 1 forced final answer
    assert "tools" not in client.calls[-1]


def test_findings_json_roundtrip_is_plain_data():
    kept, _ = clean_findings("security", [Finding(**finding())], INPUT)
    assert json.loads(json.dumps(kept[0].model_dump()))["title"] == "Hardcoded secret"
