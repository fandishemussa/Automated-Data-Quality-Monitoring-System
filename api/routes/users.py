"""User authentication and admin user management API routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status

from api.identity import get_request_identity
from api.security import require_api_token
from services.user_management_service import (
    approve_profile_update_request,
    authenticate_user,
    create_user,
    deactivate_user,
    get_profile_for_username,
    list_users,
    list_profile_update_requests,
    reject_profile_update_request,
    submit_profile_update,
    update_user,
)
from services.user_token_service import create_user_session_token
from utils.audit_logger import log_audit_event
from utils.logger import get_logger


logger = get_logger(__name__)
router = APIRouter(prefix="/api/v1", tags=["users"])


@router.post("/auth/login")
def login(payload: dict[str, Any], request: Request) -> dict[str, Any]:
    """Authenticate a dashboard user and return a signed session token."""

    username = str(payload.get("username") or "").strip()
    password = str(payload.get("password") or "")
    if not username or not password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username and password are required.")

    try:
        user = authenticate_user(username, password)
    except Exception:
        logger.exception("Dashboard login failed unexpectedly.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Login service is unavailable. Run database initialization and check backend logs.",
        )

    if user is None:
        log_audit_event(
            "USER_LOGIN_FAILED",
            username=username,
            role="unknown",
            entity_type="dashboard_user",
            entity_id=username,
            new_value={"reason": "invalid_credentials"},
            ip_address=_client_ip(request),
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password.")

    token = create_user_session_token(user)
    log_audit_event(
        "USER_LOGIN",
        username=user.get("username"),
        role=user.get("role"),
        entity_type="dashboard_user",
        entity_id=str(user.get("id")),
        ip_address=_client_ip(request),
    )
    return {"token": token, "user": user}


@router.get("/users", dependencies=[Depends(require_api_token)])
def get_users(request: Request) -> list[dict[str, Any]]:
    """Return dashboard users for administrators."""

    _require_admin(request)
    try:
        return list_users()
    except Exception:
        logger.exception("User list request failed.")
        raise HTTPException(status_code=503, detail="Users are unavailable. Check backend logs.")


@router.get("/users/me", dependencies=[Depends(require_api_token)])
def get_current_user_profile(request: Request) -> dict[str, Any]:
    """Return the current user's dashboard profile."""

    identity = get_request_identity(request)
    try:
        return get_profile_for_username(identity["username"])
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except Exception:
        logger.exception("Current user profile request failed.")
        raise HTTPException(status_code=503, detail="User profile is unavailable. Check backend logs.")


@router.post("/users/me/profile-updates", dependencies=[Depends(require_api_token)])
def post_current_user_profile_update(payload: dict[str, Any], request: Request) -> dict[str, Any]:
    """Submit a profile update request for admin approval."""

    identity = get_request_identity(request)
    try:
        update = submit_profile_update(identity["username"], payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception:
        logger.exception("Profile update submission failed.")
        raise HTTPException(status_code=503, detail="Unable to submit profile update. Check backend logs.")

    log_audit_event(
        "USER_PROFILE_UPDATE_SUBMITTED",
        username=identity["username"],
        role=identity["role"],
        entity_type="dashboard_user_profile_update",
        entity_id=str(update.get("id")),
        new_value=update.get("requested_changes"),
        ip_address=_client_ip(request),
    )
    return update


@router.get("/users/profile-updates", dependencies=[Depends(require_api_token)])
def get_profile_updates(
    request: Request,
    status_filter: str | None = None,
) -> list[dict[str, Any]]:
    """Return profile update requests for admin review."""

    _require_admin(request)
    try:
        return list_profile_update_requests(status=status_filter)
    except Exception:
        logger.exception("Profile update list request failed.")
        raise HTTPException(status_code=503, detail="Profile update requests are unavailable. Check backend logs.")


@router.patch("/users/profile-updates/{update_id}/approve", dependencies=[Depends(require_api_token)])
def approve_profile_update(update_id: int, payload: dict[str, Any], request: Request) -> dict[str, Any]:
    """Approve a profile update request and apply the changes."""

    identity = _require_admin(request)
    try:
        update = approve_profile_update_request(update_id, identity["username"], payload.get("review_notes"))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception:
        logger.exception("Profile update approval failed.")
        raise HTTPException(status_code=503, detail="Unable to approve profile update. Check backend logs.")

    log_audit_event(
        "USER_PROFILE_UPDATE_APPROVED",
        username=identity["username"],
        role=identity["role"],
        entity_type="dashboard_user_profile_update",
        entity_id=str(update_id),
        new_value=update,
        ip_address=_client_ip(request),
    )
    return update


@router.patch("/users/profile-updates/{update_id}/reject", dependencies=[Depends(require_api_token)])
def reject_profile_update(update_id: int, payload: dict[str, Any], request: Request) -> dict[str, Any]:
    """Reject a profile update request without applying changes."""

    identity = _require_admin(request)
    try:
        update = reject_profile_update_request(update_id, identity["username"], payload.get("review_notes"))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception:
        logger.exception("Profile update rejection failed.")
        raise HTTPException(status_code=503, detail="Unable to reject profile update. Check backend logs.")

    log_audit_event(
        "USER_PROFILE_UPDATE_REJECTED",
        username=identity["username"],
        role=identity["role"],
        entity_type="dashboard_user_profile_update",
        entity_id=str(update_id),
        new_value=update,
        ip_address=_client_ip(request),
    )
    return update


@router.post("/users", dependencies=[Depends(require_api_token)])
def post_user(payload: dict[str, Any], request: Request) -> dict[str, Any]:
    """Create a dashboard user."""

    identity = _require_admin(request)
    try:
        user = create_user(payload, identity["username"])
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception:
        logger.exception("User creation request failed.")
        raise HTTPException(status_code=503, detail="Unable to create user. Check backend logs.")

    log_audit_event(
        "USER_CREATED",
        username=identity["username"],
        role=identity["role"],
        entity_type="dashboard_user",
        entity_id=str(user.get("id")),
        new_value={"username": user.get("username"), "role": user.get("role")},
        ip_address=_client_ip(request),
    )
    return user


@router.patch("/users/{user_id}", dependencies=[Depends(require_api_token)])
def patch_user(user_id: int, payload: dict[str, Any], request: Request) -> dict[str, Any]:
    """Update a dashboard user."""

    identity = _require_admin(request)
    try:
        user = update_user(user_id, payload, identity["username"])
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except Exception:
        logger.exception("User update request failed.")
        raise HTTPException(status_code=503, detail="Unable to update user. Check backend logs.")

    log_audit_event(
        "USER_UPDATED",
        username=identity["username"],
        role=identity["role"],
        entity_type="dashboard_user",
        entity_id=str(user_id),
        new_value={"username": user.get("username"), "role": user.get("role"), "is_active": user.get("is_active")},
        ip_address=_client_ip(request),
    )
    return user


@router.delete("/users/{user_id}", dependencies=[Depends(require_api_token)])
def delete_user(user_id: int, request: Request) -> dict[str, Any]:
    """Deactivate a dashboard user."""

    identity = _require_admin(request)
    try:
        user = deactivate_user(user_id, identity["username"])
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except Exception:
        logger.exception("User deactivation request failed.")
        raise HTTPException(status_code=503, detail="Unable to deactivate user. Check backend logs.")

    log_audit_event(
        "USER_DEACTIVATED",
        username=identity["username"],
        role=identity["role"],
        entity_type="dashboard_user",
        entity_id=str(user_id),
        ip_address=_client_ip(request),
    )
    return user


def _require_admin(request: Request) -> dict[str, str]:
    identity = get_request_identity(request)
    if identity["role"] != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role is required.")
    return identity


def _client_ip(request: Request) -> str | None:
    if request.client is None:
        return None
    return request.client.host
