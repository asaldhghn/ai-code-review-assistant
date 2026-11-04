"""Test doubles: a scripted stand-in for the OpenAI client. No network, no cost."""

import json
from types import SimpleNamespace

import httpx
import openai


def finding(**overrides) -> dict:
    data = {
        "path": "snippet.py",
        "line": 2,
        "severity": "critical",
        "category": "security",
        "title": "Hardcoded secret",
        "description": "`key` is a literal credential.",
        "why_it_matters": "Anyone who can read the repo can use it.",
        "suggestion": "Load it from the environment.",
    }
    data.update(overrides)
    return data


def reply(*findings: dict) -> str:
    return json.dumps({"findings": list(findings)})


def message(content: str | None = None, tool_calls: list | None = None, finish: str = "stop"):
    msg = SimpleNamespace(content=content, tool_calls=tool_calls)
    usage = SimpleNamespace(prompt_tokens=10, completion_tokens=5)
    return SimpleNamespace(choices=[SimpleNamespace(message=msg, finish_reason=finish)], usage=usage)


def tool_call(name: str, arguments: dict, call_id: str = "call_1"):
    return SimpleNamespace(id=call_id, function=SimpleNamespace(name=name, arguments=json.dumps(arguments)))


def status_error(cls, status: int, text: str = "boom"):
    request = httpx.Request("POST", "https://example.invalid/v1/chat/completions")
    response = httpx.Response(status, request=request, json={"error": {"message": text}})
    return cls(text, response=response, body=None)


def connection_error():
    return openai.APIConnectionError(request=httpx.Request("POST", "https://example.invalid"))


class FakeClient:
    """Pops one scripted response per chat completion call.

    A script item may be a string (the assistant's reply text), a ready-made response from
    `message(...)`, or an Exception instance to raise.
    """

    def __init__(self, script: list | None = None, default: str | None = None):
        self.script = list(script or [])
        self.default = default
        self.calls: list[dict] = []
        self.closed = False
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    async def _create(self, **kwargs):
        self.calls.append(kwargs)
        if self.script:
            item = self.script.pop(0)
        elif self.default is not None:
            item = self.default
        else:
            raise AssertionError("FakeClient script exhausted")
        if isinstance(item, Exception):
            raise item
        if isinstance(item, str):
            return message(item)
        return item

    async def close(self):
        self.closed = True
