from auth.dashboard_auth import (
    AUTHENTICATED_SESSION_KEY,
    AUTHENTICATED_USER_SESSION_KEY,
    clear_dashboard_login_state,
    hash_password_sha256,
    is_dashboard_auth_enabled,
    is_logged_in,
    mark_logged_in,
    password_matches,
    verify_dashboard_credentials,
)


def test_is_dashboard_auth_enabled_parses_truthy_values():
    assert is_dashboard_auth_enabled("true") is True
    assert is_dashboard_auth_enabled("TRUE") is True
    assert is_dashboard_auth_enabled("1") is True
    assert is_dashboard_auth_enabled("yes") is True


def test_is_dashboard_auth_enabled_defaults_false_for_disabled_values(monkeypatch):
    monkeypatch.delenv("DASHBOARD_AUTH_ENABLED", raising=False)

    assert is_dashboard_auth_enabled() is False
    assert is_dashboard_auth_enabled("false") is False
    assert is_dashboard_auth_enabled("0") is False
    assert is_dashboard_auth_enabled("") is False


def test_verify_dashboard_credentials_accepts_correct_plain_password():
    assert verify_dashboard_credentials(
        submitted_username="admin",
        submitted_password="change_me",
        expected_username="admin",
        expected_password="change_me",
    ) is True


def test_verify_dashboard_credentials_rejects_wrong_password():
    assert verify_dashboard_credentials(
        submitted_username="admin",
        submitted_password="wrong",
        expected_username="admin",
        expected_password="change_me",
    ) is False


def test_password_matches_supports_sha256_hash():
    password_hash = hash_password_sha256("change_me")

    assert password_matches(
        submitted_password="change_me",
        expected_password_hash=password_hash,
    ) is True
    assert password_matches(
        submitted_password="wrong",
        expected_password_hash=password_hash,
    ) is False


def test_login_state_helpers_mark_and_clear_session_state():
    session_state = {}

    assert is_logged_in(session_state) is False

    mark_logged_in(session_state, "admin")

    assert is_logged_in(session_state) is True
    assert session_state[AUTHENTICATED_SESSION_KEY] is True
    assert session_state[AUTHENTICATED_USER_SESSION_KEY] == "admin"

    clear_dashboard_login_state(session_state)

    assert is_logged_in(session_state) is False
    assert AUTHENTICATED_SESSION_KEY not in session_state
    assert AUTHENTICATED_USER_SESSION_KEY not in session_state
