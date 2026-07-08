"""Signed session tokens for frontend user authentication."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import Any

from config.settings import get_env, get_int_env


TOKEN_PREFIX = "dq_user"


def create_user_session_token(user: dict[str, Any], ttl_seconds: int | None = None) -> str:
    """Create a signed session token for an authenticated dashboard user."""

    now = int(time.time())
    expires_in = ttl_seconds or get_int_env("USER_SESSION_TTL_SECONDS", 12 * 60 * 60)
    payload = {
        "username": user.get("username"),
        "role": user.get("role"),
        "full_name": user.get("full_name"),
        "iat": now,
        "exp": now + expires_in,
    }
    payload_part = _b64encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signature = _sign(payload_part)
    return f"{TOKEN_PREFIX}.{payload_part}.{signature}"


def verify_user_session_token(token: str | None) -> dict[str, Any] | None:
    """Return the token payload when valid, otherwise None."""

    if not token:
        return None

    parts = str(token).split(".")
    if len(parts) != 3 or parts[0] != TOKEN_PREFIX:
        return None

    payload_part = parts[1]
    expected_signature = _sign(payload_part)
    if not hmac.compare_digest(parts[2], expected_signature):
        return None

    try:
        payload = json.loads(_b64decode(payload_part).decode("utf-8"))
    except (ValueError, json.JSONDecodeError):
        return None

    if int(payload.get("exp", 0)) < int(time.time()):
        return None

    return payload


def _secret() -> bytes:
    """Return the HMAC secret used for user session tokens."""

    secret = get_env("USER_SESSION_SECRET") or get_env("API_TOKEN") or "change_me"
    return str(secret).encode("utf-8")


def _sign(payload_part: str) -> str:
    digest = hmac.new(_secret(), payload_part.encode("utf-8"), hashlib.sha256).digest()
    return _b64encode(digest)


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _b64decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)
