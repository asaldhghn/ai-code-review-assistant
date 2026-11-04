"""A public demo deployment must never be able to reach an AI provider (no paid calls)."""

import re
from pathlib import Path

from fastapi.testclient import TestClient

from code_review.api import create_app
from code_review.config import Settings, load_settings

ROOT = Path(__file__).resolve().parents[2]
KEY = "sk-user-key-abcdef123456"


def exploding_factory(settings, key):
    raise AssertionError("an AI client was created on a demo-only deployment")


def test_demo_only_server_never_creates_an_ai_client_even_with_server_and_request_keys():
    settings = Settings(api_key="sk-server-key-abcdef123456", enable_live_review=False)
    client = TestClient(create_app(settings, client_factory=exploding_factory, frontend_dist=None))

    for headers in ({}, {"X-Api-Key": KEY}):
        response = client.post("/api/review", json={"code": "x = 1", "mode": "live"}, headers=headers)
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "live_review_disabled"
    assert client.post("/api/review", json={"code": "x = 1"}).status_code == 200  # demo still works
    assert client.get("/api/config").json()["live_review_enabled"] is False


def test_live_flag_defaults_and_parsing(monkeypatch):
    monkeypatch.setattr("code_review.config.load_dotenv", lambda *a, **k: None)
    monkeypatch.delenv("ENABLE_LIVE_REVIEW", raising=False)
    assert load_settings().enable_live_review is True  # local development default
    for value in ("false", "False", "0", "no", "off"):
        monkeypatch.setenv("ENABLE_LIVE_REVIEW", value)
        assert load_settings().enable_live_review is False


def test_dockerfile_and_render_blueprint_both_disable_live_reviews():
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert re.search(r"ENABLE_LIVE_REVIEW=false", dockerfile)
    render = (ROOT / "render.yaml").read_text(encoding="utf-8")
    assert re.search(r"key:\s*ENABLE_LIVE_REVIEW\s*\n\s*value:\s*\"false\"", render)


def test_no_secret_environment_variables_are_declared_in_deployment_files():
    for name in ("Dockerfile", "render.yaml"):
        lines = (ROOT / name).read_text(encoding="utf-8").splitlines()
        # Comments may legitimately warn about keys; only declarations matter.
        text = "\n".join(line for line in lines if not line.lstrip().startswith("#"))
        assert not re.search(r"(API_KEY|OPENROUTER)", text, re.IGNORECASE), name
