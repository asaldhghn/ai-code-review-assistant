"""Exercise the real OpenAI SDK against a mocked HTTP transport (no network, no cost).

This checks what a fake Python client cannot: the actual request we put on the wire (URL, auth
header, strict JSON schema) and how real SDK errors map to our typed errors.
"""

import json

import httpx

from code_review.config import Settings
from code_review.providers import create_client
from code_review.schemas import ReviewRequest
from code_review.service import run_review

from .conftest import VULNERABLE
from .fakes import finding, reply

KEY = "sk-provider-zzzz99999999"
SETTINGS = Settings(max_code_chars=2000, base_url="https://provider.example/api/v1", sdk_max_retries=0)


def completion(content: str) -> dict:
    return {
        "id": "x",
        "object": "chat.completion",
        "created": 0,
        "model": "m",
        "choices": [{"index": 0, "finish_reason": "stop", "message": {"role": "assistant", "content": content}}],
        "usage": {"prompt_tokens": 3, "completion_tokens": 2, "total_tokens": 5},
    }


def factory_with(handler):
    def build(settings, key):
        return create_client(settings, key, httpx.AsyncClient(transport=httpx.MockTransport(handler)))

    return build


async def test_request_on_the_wire_and_parsed_response():
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=completion(reply(finding())))

    result = await run_review(
        ReviewRequest(code=VULNERABLE, mode="live", reviewers=["security"]),
        SETTINGS,
        api_key=KEY,
        client_factory=factory_with(handler),
    )
    assert result.summary.total == 1 and not result.is_demo

    request = seen[0]
    assert str(request.url) == "https://provider.example/api/v1/chat/completions"
    assert request.headers["authorization"] == f"Bearer {KEY}"
    body = json.loads(request.content)
    assert body["model"] == SETTINGS.security_model
    assert body["response_format"]["type"] == "json_schema"
    assert body["response_format"]["json_schema"]["strict"] is True
    assert "tools" not in body  # the web path never offers tools
    assert "snippet.py" in body["messages"][1]["content"]
    assert KEY not in json.dumps(body)  # the key is only in the header, never in the prompt


async def test_real_sdk_http_errors_map_to_typed_errors():
    import pytest

    from code_review.errors import InvalidCredentialsError, RateLimitedError

    for status, expected in [(401, InvalidCredentialsError), (429, RateLimitedError)]:

        def handler(request, status=status):
            return httpx.Response(status, json={"error": {"message": f"nope {KEY}"}})

        with pytest.raises(expected) as exc:
            await run_review(
                ReviewRequest(code=VULNERABLE, mode="live", reviewers=["security"]),
                SETTINGS,
                api_key=KEY,
                client_factory=factory_with(handler),
            )
        assert KEY not in exc.value.message


async def test_network_failure_and_garbage_body_are_handled():
    import pytest

    from code_review.errors import InvalidModelResponseError, ProviderUnavailableError

    def down(request):
        raise httpx.ConnectError("refused", request=request)

    with pytest.raises(ProviderUnavailableError):
        await run_review(
            ReviewRequest(code=VULNERABLE, mode="live", reviewers=["security"]),
            SETTINGS,
            api_key=KEY,
            client_factory=factory_with(down),
        )

    def garbage(request):
        return httpx.Response(200, json=completion("I refuse to answer in JSON"))

    with pytest.raises(InvalidModelResponseError):
        await run_review(
            ReviewRequest(code=VULNERABLE, mode="live", reviewers=["security"]),
            SETTINGS,
            api_key=KEY,
            client_factory=factory_with(garbage),
        )
