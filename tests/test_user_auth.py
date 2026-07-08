from services.user_management_service import hash_password, verify_password
from services.user_token_service import create_user_session_token, verify_user_session_token


def test_password_hash_roundtrip():
    password_hash = hash_password("secret-password")

    assert password_hash != "secret-password"
    assert verify_password("secret-password", password_hash) is True
    assert verify_password("wrong-password", password_hash) is False


def test_user_session_token_roundtrip(monkeypatch):
    monkeypatch.setenv("USER_SESSION_SECRET", "test-session-secret")

    token = create_user_session_token(
        {"username": "admin", "role": "admin", "full_name": "Admin User"},
        ttl_seconds=60,
    )
    payload = verify_user_session_token(token)

    assert payload is not None
    assert payload["username"] == "admin"
    assert payload["role"] == "admin"


def test_expired_user_session_token_is_rejected(monkeypatch):
    monkeypatch.setenv("USER_SESSION_SECRET", "test-session-secret")

    token = create_user_session_token({"username": "viewer", "role": "viewer"}, ttl_seconds=-1)

    assert verify_user_session_token(token) is None
