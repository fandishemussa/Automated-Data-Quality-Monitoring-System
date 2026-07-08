"""Request identity helpers shared by protected API routes."""

from __future__ import annotations

from fastapi import Request

from api.security import get_api_token_header_name
from config.settings import get_env
from services.data_cleaning_policy import normalize_role
from services.user_token_service import verify_user_session_token


def get_request_identity(request: Request) -> dict[str, str]:
    """Resolve caller identity from a signed user token or trusted internal headers."""

    token_payload = verify_user_session_token(request.headers.get(get_api_token_header_name()))
    if token_payload:
        return {
            "username": str(token_payload.get("username") or "api_user"),
            "role": normalize_role(token_payload.get("role") or "viewer"),
        }

    return {
        "username": request.headers.get("X-User") or "api_user",
        "role": normalize_role(request.headers.get("X-User-Role") or get_env("API_DEFAULT_ROLE", "admin")),
    }
