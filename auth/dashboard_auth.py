"""Streamlit dashboard authentication helpers."""

from __future__ import annotations

import hashlib
import hmac
import os
from pathlib import Path
from typing import Any, MutableMapping

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")

DASHBOARD_AUTH_ENABLED_ENV = "DASHBOARD_AUTH_ENABLED"
DASHBOARD_USERNAME_ENV = "DASHBOARD_USERNAME"
DASHBOARD_PASSWORD_ENV = "DASHBOARD_PASSWORD"
DASHBOARD_PASSWORD_HASH_ENV = "DASHBOARD_PASSWORD_HASH"

AUTHENTICATED_SESSION_KEY = "dashboard_authenticated"
AUTHENTICATED_USER_SESSION_KEY = "dashboard_authenticated_user"

TRUE_VALUES = {"1", "true", "yes", "y", "on"}


def is_dashboard_auth_enabled(value: Any | None = None) -> bool:
    """Return whether dashboard authentication should be enforced."""

    raw_value = (
        os.getenv(DASHBOARD_AUTH_ENABLED_ENV, "false")
        if value is None
        else value
    )
    return str(raw_value).strip().lower() in TRUE_VALUES


def get_dashboard_credentials() -> dict[str, str]:
    """Read dashboard credentials from environment variables."""

    return {
        "username": os.getenv(DASHBOARD_USERNAME_ENV, ""),
        "password": os.getenv(DASHBOARD_PASSWORD_ENV, ""),
        "password_hash": os.getenv(DASHBOARD_PASSWORD_HASH_ENV, ""),
    }


def hash_password_sha256(password: str) -> str:
    """Create a SHA-256 password hash for optional hashed-password support."""

    return hashlib.sha256((password or "").encode("utf-8")).hexdigest()


def password_matches(
    submitted_password: str,
    expected_password: str = "",
    expected_password_hash: str = "",
) -> bool:
    """Compare a submitted password with plain or SHA-256-hashed credentials."""

    submitted_password = submitted_password or ""
    expected_password = expected_password or ""
    expected_password_hash = (expected_password_hash or "").strip().lower()

    if expected_password_hash:
        submitted_hash = hash_password_sha256(submitted_password)
        return hmac.compare_digest(submitted_hash, expected_password_hash)

    if not expected_password:
        return False

    return hmac.compare_digest(submitted_password, expected_password)


def credentials_are_configured(
    username: str = "",
    password: str = "",
    password_hash: str = "",
) -> bool:
    """Return whether enough credential data exists to authenticate a user."""

    return bool(username and (password or password_hash))


def verify_dashboard_credentials(
    submitted_username: str,
    submitted_password: str,
    expected_username: str | None = None,
    expected_password: str | None = None,
    expected_password_hash: str | None = None,
) -> bool:
    """Verify submitted dashboard credentials using constant-time comparisons."""

    credentials = get_dashboard_credentials()
    username = credentials["username"] if expected_username is None else expected_username
    password = credentials["password"] if expected_password is None else expected_password
    password_hash = (
        credentials["password_hash"]
        if expected_password_hash is None
        else expected_password_hash
    )

    if not credentials_are_configured(username, password, password_hash):
        return False

    username_matches = hmac.compare_digest(
        submitted_username or "",
        username,
    )
    return username_matches and password_matches(
        submitted_password=submitted_password,
        expected_password=password,
        expected_password_hash=password_hash,
    )


def is_logged_in(session_state: MutableMapping[str, Any]) -> bool:
    """Return whether a Streamlit session has been authenticated."""

    return bool(session_state.get(AUTHENTICATED_SESSION_KEY, False))


def mark_logged_in(
    session_state: MutableMapping[str, Any],
    username: str,
) -> None:
    """Store successful login state in the Streamlit session."""

    session_state[AUTHENTICATED_SESSION_KEY] = True
    session_state[AUTHENTICATED_USER_SESSION_KEY] = username


def clear_dashboard_login_state(session_state: MutableMapping[str, Any]) -> None:
    """Clear dashboard login values from a Streamlit session."""

    session_state.pop(AUTHENTICATED_SESSION_KEY, None)
    session_state.pop(AUTHENTICATED_USER_SESSION_KEY, None)


def require_dashboard_login() -> bool:
    """Require a valid dashboard login when dashboard auth is enabled."""

    if not is_dashboard_auth_enabled():
        return True

    import streamlit as st
    from ui.theme import get_brand_config

    if is_logged_in(st.session_state):
        return True

    from ui.theme import brand_mark_html

    brand = get_brand_config()
    st.markdown(
        """
        <style>
            section[data-testid="stSidebar"],
            div[data-testid="stSidebarCollapsedControl"] {
                display: none;
            }

            .block-container {
                max-width: 460px !important;
                min-height: 100vh;
                padding: 8vh 1rem 2rem !important;
                display: flex;
                flex-direction: column;
                justify-content: center;
            }

            div[data-testid="stForm"] {
                background: var(--surface);
                border: 1px solid var(--border);
                border-radius: 14px;
                box-shadow: var(--shadow);
                padding: 1.35rem 1.35rem 1.15rem;
            }

            div[data-testid="stForm"] label {
                color: var(--text-main);
                font-weight: 650;
            }

            div[data-testid="stForm"] input {
                min-height: 42px;
            }

            div[data-testid="stFormSubmitButton"] button {
                width: 100%;
                min-height: 42px;
                margin-top: 0.25rem;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )

    with st.form("dashboard_login_form"):
        st.markdown(
            f"""
            <div class="login-card-brand">
                {brand_mark_html(brand, size=56)}
                <div class="login-title">{_escape(brand.app_name)}</div>
                <div class="login-subtitle">Secure Data Quality Monitoring Portal</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Log in")

        login_error = ""

        if submitted:
            credentials = get_dashboard_credentials()

            if not credentials_are_configured(**credentials):
                login_error = (
                    "Dashboard authentication is enabled, but credentials are not configured."
                )
            elif verify_dashboard_credentials(username, password):
                mark_logged_in(st.session_state, username)
                st.rerun()
                return True
            else:
                login_error = "Invalid username or password."

        if login_error:
            st.error(login_error)

        st.markdown(
            '<div class="login-access-note">Protected dashboard access</div>',
            unsafe_allow_html=True,
        )

    return False


def _escape(value: object) -> str:
    """Escape small HTML text fragments used on the login page."""

    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
