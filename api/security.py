"""FastAPI authentication helpers for internal API access."""

from __future__ import annotations

import hmac
from typing import Any

from fastapi import HTTPException, Request, status

from config.settings import get_bool_env, get_env
from services.user_token_service import verify_user_session_token
from utils.audit_logger import log_audit_event


DEFAULT_TOKEN_HEADER = "X-API-Key"


def is_api_auth_enabled(value: Any | None = None) -> bool:
    """Return whether API token authentication should be enforced."""

    if value is None:
        return get_bool_env("API_AUTH_ENABLED", True)

    return str(value).strip().lower() in {"true", "1", "yes", "y", "on"}


def verify_api_token(
    submitted_token: str | None,
    expected_token: str | None = None,
) -> bool:
    """Verify a static API token or signed dashboard user session token."""

    configured_token = expected_token
    if configured_token is None:
        configured_token = get_env("API_TOKEN", default="")

    submitted = (submitted_token or "").strip()
    expected = (configured_token or "").strip()

    if not submitted:
        return False

    if expected and hmac.compare_digest(submitted, expected):
        return True

    return verify_user_session_token(submitted) is not None


def get_api_token_header_name() -> str:
    """Return the configured API token header name."""

    header_name = get_env("API_TOKEN_HEADER", default=DEFAULT_TOKEN_HEADER)
    return str(header_name or DEFAULT_TOKEN_HEADER).strip() or DEFAULT_TOKEN_HEADER


def require_api_token(request: Request) -> None:
    """FastAPI dependency that requires a valid API token when enabled."""

    if not is_api_auth_enabled():
        return None

    header_name = get_api_token_header_name()
    submitted_token = request.headers.get(header_name)

    if not submitted_token:
        log_audit_event(
            "API_AUTH_FAILED",
            username="api_client",
            role="api",
            entity_type="api_request",
            entity_id=str(request.url.path),
            new_value={"reason": "missing_token"},
            ip_address=_client_ip(request),
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Missing API token. Provide it in the {header_name} header.",
        )

    if not verify_api_token(submitted_token):
        log_audit_event(
            "API_AUTH_FAILED",
            username="api_client",
            role="api",
            entity_type="api_request",
            entity_id=str(request.url.path),
            new_value={"reason": "invalid_token"},
            ip_address=_client_ip(request),
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API token.",
        )

    return None


def _client_ip(request: Request) -> str | None:
    """Return the request client IP address when available."""

    if request.client is None:
        return None
    return request.client.host
