import asyncio

import openai
import pytest

from code_review.config import Settings
from code_review.errors import (
    InvalidCredentialsError,
    InvalidInputError,
    LiveReviewDisabledError,
    MissingCredentialsError,
    PayloadTooLargeError,
    ProviderUnavailableError,
    RateLimitedError,
)
from code_review.schemas import ReviewRequest
from code_review.service import run_review, validate_api_key, validate_code

from .conftest import VULNERABLE
from .fakes import FakeClient, finding, message, reply, status_error

SETTINGS = Settings(max_code_chars=2000)


def factory_for(client):
    return lambda settings, key: client


async def test_demo_review_is_labeled_and_needs_no_credentials():
    result = await run_review(ReviewRequest(code=VULNERABLE), SETTINGS)
    assert result.is_demo and result.mode == "demo" and result.status == "complete"
    assert result.summary.total == len(result.findings) > 0
    assert any("not from an AI model" in n for n in result.notices)
    assert all("rule-based" in r.engine for r in result.reviewers)
    assert result.summary.by_severity.critical >= 2
    assert {f.id for f in result.findings if f.reviewer == "security"} >= {"S1", "S2"}


async def test_demo_respects_reviewer_selection():
    result = await run_review(ReviewRequest(code=VULNERABLE, reviewers=["maintainability"]), SETTINGS)
    assert [r.id for r in result.reviewers] == ["maintainability"]
    assert all(f.reviewer == "maintainability" for f in result.findings)


@pytest.mark.parametrize("code", ["", "   \n\t "])
def test_blank_code_rejected(code):
    with pytest.raises(InvalidInputError) as exc:
        validate_code(code, SETTINGS)
    assert exc.value.code == "empty_code"


def test_binary_and_oversized_code_rejected():
    with pytest.raises(InvalidInputError):
        validate_code("a\x00b", SETTINGS)
    with pytest.raises(PayloadTooLargeError):
        validate_code("x" * 2001, SETTINGS)


@pytest.mark.parametrize("key", ["has space", "x" * 301, "tab\there"])
def test_malformed_api_keys_rejected(key):
    with pytest.raises(InvalidInputError):
        validate_api_key(key)


def test_blank_api_key_is_treated_as_missing():
    assert validate_api_key("   ") is None and validate_api_key(None) is None


async def test_live_review_disabled_on_demo_only_servers():
    with pytest.raises(LiveReviewDisabledError):
        await run_review(
            ReviewRequest(code=VULNERABLE, mode="live"), Settings(enable_live_review=False), api_key="sk-abcdefgh12345"
        )


async def test_live_review_requires_a_key():
    with pytest.raises(MissingCredentialsError):
        await run_review(ReviewRequest(code=VULNERABLE, mode="live"), SETTINGS)


async def test_live_review_with_request_key_returns_non_demo_result_and_closes_client():
    client = FakeClient([reply(finding()), reply(finding(category="naming", title="Vague name"))])
    result = await run_review(
        ReviewRequest(code=VULNERABLE, mode="live"),
        SETTINGS,
        api_key="sk-live-abcdef123456",
        client_factory=factory_for(client),
    )
    assert not result.is_demo and result.mode == "live" and result.status == "complete"
    assert result.summary.total == 2
    assert client.closed
    assert result.reviewers[0].engine == SETTINGS.security_model
    assert all(call["model"] == SETTINGS.security_model for call in client.calls)


async def test_live_review_can_use_the_server_key():
    client = FakeClient(default=reply())
    settings = Settings(api_key="sk-server-abcdef123456", max_code_chars=2000)
    seen = {}

    def factory(s, key):
        seen["key"] = key
        return client

    result = await run_review(ReviewRequest(code=VULNERABLE, mode="live"), settings, client_factory=factory)
    assert seen["key"] == "sk-server-abcdef123456" and result.summary.total == 0


async def test_one_failed_reviewer_gives_a_partial_result():
    class Split(FakeClient):
        async def _create(self, **kwargs):
            if "Maintainability Critic" in kwargs["messages"][0]["content"]:
                raise status_error(openai.RateLimitError, 429)
            return message(reply(finding()))

    result = await run_review(
        ReviewRequest(code=VULNERABLE, mode="live"),
        SETTINGS,
        api_key="sk-live-abcdef123456",
        client_factory=factory_for(Split()),
    )
    assert result.status == "partial"
    failed = next(r for r in result.reviewers if r.status == "failed")
    assert failed.error_code == "rate_limited"
    assert any("could not complete" in n for n in result.notices)
    assert result.summary.total == 1


async def test_all_reviewers_failing_raises_the_most_actionable_error():
    client = FakeClient([status_error(openai.AuthenticationError, 401), status_error(openai.RateLimitError, 429)])
    with pytest.raises(InvalidCredentialsError):
        await run_review(
            ReviewRequest(code=VULNERABLE, mode="live"),
            SETTINGS,
            api_key="sk-live-abcdef123456",
            client_factory=factory_for(client),
        )


async def test_rate_limit_error_surfaces_when_all_reviewers_are_limited():
    client = FakeClient(default=None)
    client.script = [status_error(openai.RateLimitError, 429)] * 2
    with pytest.raises(RateLimitedError):
        await run_review(
            ReviewRequest(code=VULNERABLE, mode="live"),
            SETTINGS,
            api_key="sk-live-abcdef123456",
            client_factory=factory_for(client),
        )


async def test_timeout_is_reported_as_provider_unavailable():
    class Slow(FakeClient):
        async def _create(self, **kwargs):
            await asyncio.sleep(5)

    settings = Settings(max_code_chars=2000, request_timeout_seconds=0.05)  # shortened for the test
    with pytest.raises(ProviderUnavailableError):
        await run_review(
            ReviewRequest(code=VULNERABLE, mode="live"),
            settings,
            api_key="sk-live-abcdef123456",
            client_factory=factory_for(Slow()),
        )
