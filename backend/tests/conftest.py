import pytest
from fastapi.testclient import TestClient

from code_review.api import create_app
from code_review.config import Settings

from .fakes import FakeClient

VULNERABLE = (
    "import os\n"
    'api_key = "sk-live-abcdef123456"\n'
    "def get_user(db, name):\n"
    '    q = "SELECT * FROM users WHERE name = \'" + name + "\'"\n'
    "    return db.execute(q)\n"
)


@pytest.fixture
def settings() -> Settings:
    return Settings(api_key=None, max_code_chars=2000, live_rate_limit_per_minute=3)


@pytest.fixture
def fake_client() -> FakeClient:
    return FakeClient()


@pytest.fixture
def make_app(settings, fake_client):
    def build(**overrides):
        merged = Settings(**{**settings.__dict__, **overrides.pop("settings", {})})
        return create_app(merged, client_factory=lambda s, key: fake_client, frontend_dist=None, **overrides)

    return build


@pytest.fixture
def client(make_app) -> TestClient:
    return TestClient(make_app())
