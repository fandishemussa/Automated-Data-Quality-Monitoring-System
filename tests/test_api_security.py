from fastapi.testclient import TestClient

from api.app import app
from api.security import is_api_auth_enabled, verify_api_token
from services.user_token_service import create_user_session_token


def _mock_empty_fetch(monkeypatch):
    """Avoid real database access in API authentication tests."""

    monkeypatch.setattr("api.app.fetch_all", lambda query, params=None: [])


def test_is_api_auth_enabled_parses_values(monkeypatch):
    monkeypatch.delenv("API_AUTH_ENABLED", raising=False)

    assert is_api_auth_enabled("true") is True
    assert is_api_auth_enabled("1") is True
    assert is_api_auth_enabled("false") is False
    assert is_api_auth_enabled("0") is False


def test_verify_api_token_accepts_correct_token():
    assert verify_api_token("secret-token", expected_token="secret-token") is True
    assert verify_api_token("wrong-token", expected_token="secret-token") is False
    assert verify_api_token("", expected_token="secret-token") is False


def test_verify_api_token_accepts_signed_user_session(monkeypatch):
    monkeypatch.setenv("USER_SESSION_SECRET", "test-session-secret")
    token = create_user_session_token({"username": "admin", "role": "admin"}, ttl_seconds=60)

    assert verify_api_token(token, expected_token="static-token") is True


def test_auth_disabled_allows_access(monkeypatch):
    _mock_empty_fetch(monkeypatch)
    monkeypatch.setenv("API_AUTH_ENABLED", "false")

    client = TestClient(app)
    response = client.get("/api/v1/runs")

    assert response.status_code == 200
    assert response.json() == []


def test_auth_enabled_blocks_missing_token(monkeypatch):
    _mock_empty_fetch(monkeypatch)
    monkeypatch.setattr("api.security.log_audit_event", lambda *args, **kwargs: True)
    monkeypatch.setenv("API_AUTH_ENABLED", "true")
    monkeypatch.setenv("API_TOKEN", "secret-token")
    monkeypatch.setenv("API_TOKEN_HEADER", "X-API-Key")

    client = TestClient(app)
    response = client.get("/api/v1/runs")

    assert response.status_code == 401


def test_auth_enabled_accepts_correct_token(monkeypatch):
    _mock_empty_fetch(monkeypatch)
    monkeypatch.setenv("API_AUTH_ENABLED", "true")
    monkeypatch.setenv("API_TOKEN", "secret-token")
    monkeypatch.setenv("API_TOKEN_HEADER", "X-API-Key")

    client = TestClient(app)
    response = client.get("/api/v1/runs", headers={"X-API-Key": "secret-token"})

    assert response.status_code == 200
    assert response.json() == []


def test_health_remains_public_when_auth_enabled(monkeypatch):
    monkeypatch.setenv("API_AUTH_ENABLED", "true")
    monkeypatch.setenv("API_TOKEN", "secret-token")

    client = TestClient(app)
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
