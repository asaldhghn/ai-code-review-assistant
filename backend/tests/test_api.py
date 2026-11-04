import json

import openai
import pytest
from fastapi.testclient import TestClient

from code_review.api import create_app

from .conftest import VULNERABLE
from .fakes import finding, reply, status_error

KEY = "sk-live-abcdef123456"


def review(client, **overrides):
    return client.post("/api/review", json={"code": VULNERABLE, "language": "python", **overrides})


# ---------- basic endpoints ----------


def test_health_and_config(client):
    assert client.get("/api/health").json()["status"] == "ok"
    cfg = client.get("/api/config").json()
    assert cfg["live_review_enabled"] is True and cfg["server_key_configured"] is False
    assert "python" in cfg["languages"] and len(cfg["reviewers"]) == 2


def test_config_never_exposes_the_server_key(make_app):
    app = make_app(settings={"api_key": KEY})
    body = TestClient(app).get("/api/config").text
    assert KEY not in body and json.loads(body)["server_key_configured"] is True


def test_security_headers_are_set(client):
    headers = client.get("/api/health").headers
    assert headers["x-content-type-options"] == "nosniff"
    assert headers["x-frame-options"] == "DENY"
    assert "frame-ancestors 'none'" in headers["content-security-policy"]


# ---------- samples ----------


def test_samples_list_and_fetch(client):
    items = client.get("/api/samples").json()
    assert {i["id"] for i in items} == {"python-user-service", "javascript-comment-widget", "python-clean-module"}
    sample = client.get("/api/samples/python-user-service").json()
    assert "SELECT * FROM users" in sample["code"]


@pytest.mark.parametrize("sample_id", ["nope", "..%2F..%2Fetc%2Fpasswd", "user_service.py", "%2e%2e%2fconfig"])
def test_samples_cannot_be_used_to_read_arbitrary_files(client, sample_id):
    response = client.get(f"/api/samples/{sample_id}")
    assert response.status_code in (404, 422)
    assert "root:" not in response.text


# ---------- demo review ----------


def test_demo_review_end_to_end(client):
    response = review(client)
    assert response.status_code == 200
    data = response.json()
    assert data["is_demo"] is True and data["mode"] == "demo"
    assert data["summary"]["total"] == len(data["findings"]) > 0
    assert set(data["summary"]["by_severity"]) == {"critical", "warn", "info"}
    first = data["findings"][0]
    assert {"id", "title", "severity", "line", "description", "why_it_matters", "suggestion", "reviewer"} <= set(first)
    assert data["filename"] == "snippet.py"


def test_filename_is_only_a_label(client):
    data = review(client, filename="../../secret/app.py").json()
    assert data["filename"] == "app.py"


def test_clean_code_returns_an_empty_but_valid_result(client):
    data = review(client, code="x = 1\n").json()
    assert data["summary"]["total"] == 0 and data["findings"] == [] and data["status"] == "complete"


# ---------- input validation ----------


def test_empty_code_is_rejected_with_a_helpful_error(client):
    response = review(client, code="   ")
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "empty_code"


def test_oversized_code_returns_413(client):
    response = review(client, code="x = 1\n" * 1000)
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "payload_too_large"


def test_oversized_request_body_is_rejected_early(client):
    response = client.post("/api/review", content=b"{" + b" " * 200_000, headers={"content-type": "application/json"})
    assert response.status_code == 413


@pytest.mark.parametrize(
    "body",
    [
        {"code": "x", "language": "cobol"},
        {"code": "x", "mode": "turbo"},
        {"code": "x", "reviewers": []},
        {"code": "x", "unknown": 1},
        {"language": "python"},
        {"code": 123},
    ],
)
def test_invalid_requests_get_a_consistent_error_shape(client, body):
    response = client.post("/api/review", json=body)
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "invalid_input" and "Invalid request" in error["message"]


def test_validation_errors_do_not_echo_the_submitted_input(client):
    response = client.post("/api/review", json={"code": "SECRET-PAYLOAD", "language": "cobol"})
    assert "SECRET-PAYLOAD" not in response.text


def test_malformed_json_is_a_clean_422(client):
    response = client.post("/api/review", content="{not json", headers={"content-type": "application/json"})
    assert response.status_code == 422


# ---------- live review ----------


def test_live_without_a_key_returns_401(client):
    response = review(client, mode="live")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "missing_credentials"


def test_live_is_forbidden_on_demo_only_deployments(make_app):
    client = TestClient(make_app(settings={"enable_live_review": False}))
    response = client.post("/api/review", json={"code": "x = 1", "mode": "live"}, headers={"X-Api-Key": KEY})
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "live_review_disabled"
    # Demo reviews still work there.
    assert client.post("/api/review", json={"code": "x = 1"}).status_code == 200


def test_live_review_with_header_key_uses_the_provider_and_is_not_labeled_demo(make_app, fake_client):
    fake_client.script = [reply(finding()), reply()]
    client = TestClient(make_app())
    response = client.post("/api/review", json={"code": VULNERABLE, "mode": "live"}, headers={"X-Api-Key": KEY})
    assert response.status_code == 200
    data = response.json()
    assert data["is_demo"] is False and data["mode"] == "live"
    assert data["findings"][0]["title"] == "Hardcoded secret"
    assert KEY not in response.text


@pytest.mark.parametrize(
    ("exc", "status", "code"),
    [
        (status_error(openai.AuthenticationError, 401, f"bad key {KEY}"), 401, "invalid_credentials"),
        (status_error(openai.RateLimitError, 429), 429, "rate_limited"),
        (status_error(openai.InternalServerError, 500), 502, "provider_unavailable"),
    ],
)
def test_provider_failures_map_to_http_errors_without_leaking_the_key(make_app, fake_client, exc, status, code):
    fake_client.script = [exc, exc]
    client = TestClient(make_app())
    response = client.post("/api/review", json={"code": VULNERABLE, "mode": "live"}, headers={"X-Api-Key": KEY})
    assert response.status_code == status
    assert response.json()["error"]["code"] == code
    assert KEY not in response.text


def test_invalid_model_output_returns_502(make_app, fake_client):
    fake_client.script = ["garbage", "garbage", "garbage", "garbage"]
    client = TestClient(make_app())
    response = client.post("/api/review", json={"code": VULNERABLE, "mode": "live"}, headers={"X-Api-Key": KEY})
    assert response.status_code == 502 and response.json()["error"]["code"] == "invalid_response"


def test_live_reviews_are_rate_limited_per_client(make_app, fake_client):
    fake_client.default = reply()
    client = TestClient(make_app())
    codes = [
        client.post("/api/review", json={"code": VULNERABLE, "mode": "live"}, headers={"X-Api-Key": KEY}).status_code
        for _ in range(5)
    ]
    assert codes == [200, 200, 200, 429, 429]
    # Demo reviews are not affected by the live limit.
    assert client.post("/api/review", json={"code": VULNERABLE}).status_code == 200


def test_unexpected_errors_return_a_generic_500(settings):
    def boom(s, key):
        raise RuntimeError(f"internal detail {KEY}")

    app = create_app(settings, client_factory=boom, frontend_dist=None)
    client = TestClient(app, raise_server_exceptions=False)
    response = client.post("/api/review", json={"code": VULNERABLE, "mode": "live"}, headers={"X-Api-Key": KEY})
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "internal_error"
    assert "internal detail" not in response.text and KEY not in response.text


# ---------- reports ----------


def test_html_report_escapes_untrusted_content(client):
    data = review(client).json()
    data["findings"][0]["title"] = "<script>alert(1)</script>"
    data["findings"][0]["suggestion"] = '"><img src=x onerror=alert(1)>'
    response = client.post("/api/reports/html", json=data)
    assert response.status_code == 200
    assert "attachment" in response.headers["content-disposition"]
    assert "<script>alert(1)" not in response.text and "<img src=x" not in response.text
    assert "&lt;script&gt;" in response.text
    assert "Content-Security-Policy" in response.text
    assert "rule-based" in response.text  # demo reports are labeled


def test_json_report_roundtrips(client):
    data = review(client).json()
    response = client.post("/api/reports/json", json=data)
    assert response.status_code == 200
    assert json.loads(response.text)["review_id"] == data["review_id"]


def test_unknown_report_format_404(client):
    data = review(client).json()
    assert client.post("/api/reports/pdf", json=data).status_code == 404


# ---------- serving the built UI ----------


@pytest.fixture
def ui_client(settings, tmp_path):
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<html>SPA</html>", encoding="utf-8")
    (dist / "assets" / "app.js").write_text("console.log(1)", encoding="utf-8")
    (tmp_path / "private.txt").write_text("private", encoding="utf-8")
    return TestClient(create_app(settings, frontend_dist=dist))


def test_spa_serves_index_assets_and_client_routes(ui_client):
    assert "SPA" in ui_client.get("/").text
    assert "SPA" in ui_client.get("/about").text
    assert ui_client.get("/assets/app.js").text == "console.log(1)"


def test_spa_fallback_does_not_hide_api_404s_or_allow_traversal(ui_client):
    assert ui_client.get("/api/nope").status_code == 404
    assert ui_client.get("/api/nope").json()["error"]["code"] == "not_found"
    assert "private" not in ui_client.get("/..%2Fprivate.txt").text
    assert "private" not in ui_client.get("/assets/..%2F..%2Fprivate.txt").text
