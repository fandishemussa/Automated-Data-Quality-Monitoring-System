"""Protected remediation and data cleaning API routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from api.identity import get_request_identity
from api.security import require_api_token
from services.data_cleaning_policy import has_permission, normalize_role
from services.data_cleaning_service import (
    approve_cleaning_job,
    create_cleaning_job,
    execute_cleaning_job,
    get_cleanable_issues,
    get_cleaning_job,
    list_cleaning_jobs,
    preview_cleaning_action,
    rollback_cleaning_job,
    suggest_cleaning_actions,
    update_issue_status,
    verify_cleaning_job,
)
from utils.audit_logger import log_audit_event
from utils.logger import get_logger


logger = get_logger(__name__)

router = APIRouter(
    prefix="/api/v1",
    tags=["remediation"],
    dependencies=[Depends(require_api_token)],
)


def _identity(request: Request) -> dict[str, str]:
    """Return API caller identity from a signed session token or headers."""

    identity = get_request_identity(request)
    identity["role"] = normalize_role(identity["role"])
    return identity


def _require(identity: dict[str, str], permission: str) -> None:
    if not has_permission(identity["role"], permission):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Role {identity['role']} does not have permission: {permission}.",
        )


def _assigned_issue_scope(identity: dict[str, str]) -> str | None:
    """Return assignee scope for roles restricted to their own remediation queue."""

    if identity["role"] == "data_analyst":
        return identity["username"]
    return None


def _ensure_issue_access(issue_id: int, identity: dict[str, str]) -> None:
    """Prevent scoped users from acting on issues outside their assignment."""

    assigned_to = _assigned_issue_scope(identity)
    if not assigned_to:
        return
    issue = next(
        (
            row for row in get_cleanable_issues(assigned_to=assigned_to)
            if int(row["id"]) == int(issue_id)
        ),
        None,
    )
    if issue is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This issue is not assigned to your remediation queue.",
        )


def _friendly_error(error: Exception) -> HTTPException:
    if isinstance(error, PermissionError):
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(error))
    if isinstance(error, ValueError):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))
    logger.exception("Remediation API request failed.")
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Remediation request failed. Check backend logs.",
    )


@router.get("/issues/cleanable")
def cleanable_issues(
    request: Request,
    run_id: int | None = Query(None),
    dataset_name: str | None = Query(None),
    status_filter: str | None = Query(None, alias="status"),
    severity: str | None = Query(None),
    identity: dict[str, str] = Depends(_identity),
) -> list[dict[str, Any]]:
    """Return data quality issues eligible for remediation."""

    _require(identity, "view_issues")
    try:
        return get_cleanable_issues(
            run_id=run_id,
            dataset_name=dataset_name,
            status=status_filter,
            severity=severity,
            assigned_to=_assigned_issue_scope(identity),
        )
    except Exception as exc:
        raise _friendly_error(exc)


@router.get("/issues/{issue_id}/suggestions")
def issue_suggestions(
    issue_id: int,
    identity: dict[str, str] = Depends(_identity),
) -> dict[str, Any]:
    """Return suggested cleaning actions for one issue."""

    _require(identity, "view_issues")
    issues = get_cleanable_issues(assigned_to=_assigned_issue_scope(identity))
    issue = next((row for row in issues if int(row["id"]) == issue_id), None)
    if issue is None:
        raise HTTPException(status_code=404, detail="Issue not found.")
    return {"issue_id": issue_id, "suggestions": suggest_cleaning_actions(issue)}


@router.post("/cleaning/preview")
def cleaning_preview(
    payload: dict[str, Any],
    request: Request,
    identity: dict[str, str] = Depends(_identity),
) -> dict[str, Any]:
    """Preview a cleaning operation without updating source data."""

    _require(identity, "create_cleaning_job")
    _ensure_issue_access(int(payload.get("issue_id") or 0), identity)
    try:
        preview = preview_cleaning_action(payload)
        log_audit_event(
            "CLEANING_PREVIEWED",
            username=identity["username"],
            role=identity["role"],
            entity_type="data_quality_issue",
            entity_id=payload.get("issue_id"),
            new_value=preview,
            ip_address=_client_ip(request),
        )
        return preview
    except Exception as exc:
        raise _friendly_error(exc)


@router.post("/cleaning/jobs")
def create_job(
    payload: dict[str, Any],
    identity: dict[str, str] = Depends(_identity),
) -> dict[str, Any]:
    """Create a cleaning job."""

    _require(identity, "create_cleaning_job")
    _ensure_issue_access(int(payload.get("issue_id") or 0), identity)
    try:
        return create_cleaning_job(payload, identity["username"], identity["role"])
    except Exception as exc:
        raise _friendly_error(exc)


@router.get("/cleaning/jobs")
def get_jobs(
    status_filter: str | None = Query(None, alias="status"),
    dataset_name: str | None = Query(None),
    requested_by: str | None = Query(None),
    identity: dict[str, str] = Depends(_identity),
) -> list[dict[str, Any]]:
    """List cleaning jobs."""

    _require(identity, "view_issues")
    try:
        return list_cleaning_jobs(
            status=status_filter,
            dataset_name=dataset_name,
            requested_by=requested_by,
            assigned_to=_assigned_issue_scope(identity),
        )
    except Exception as exc:
        raise _friendly_error(exc)


@router.get("/cleaning/jobs/{job_id}")
def get_job(
    job_id: int,
    identity: dict[str, str] = Depends(_identity),
) -> dict[str, Any]:
    """Return one cleaning job with change log."""

    _require(identity, "view_issues")
    try:
        job = get_cleaning_job(job_id)
        if _assigned_issue_scope(identity):
            _ensure_issue_access(int(job["issue_id"]), identity)
        return job
    except Exception as exc:
        raise _friendly_error(exc)


@router.patch("/cleaning/jobs/{job_id}/approve")
def approve_job(
    job_id: int,
    identity: dict[str, str] = Depends(_identity),
) -> dict[str, Any]:
    """Approve a cleaning job."""

    _require(identity, "approve_cleaning_job")
    try:
        return approve_cleaning_job(job_id, identity["username"], identity["role"])
    except Exception as exc:
        raise _friendly_error(exc)


@router.post("/cleaning/jobs/{job_id}/execute")
def execute_job(
    job_id: int,
    identity: dict[str, str] = Depends(_identity),
) -> dict[str, Any]:
    """Execute an approved cleaning job."""

    if identity["role"] == "admin":
        _require(identity, "execute_cleaning_job")
    else:
        _require(identity, "execute_approved_cleaning_job")
    try:
        job = get_cleaning_job(job_id)
        if _assigned_issue_scope(identity):
            _ensure_issue_access(int(job["issue_id"]), identity)
        return execute_cleaning_job(job_id, identity["username"], identity["role"])
    except Exception as exc:
        raise _friendly_error(exc)


@router.post("/cleaning/jobs/{job_id}/rollback")
def rollback_job(
    job_id: int,
    identity: dict[str, str] = Depends(_identity),
) -> dict[str, Any]:
    """Rollback an executed cleaning job."""

    _require(identity, "rollback_cleaning_job")
    try:
        return rollback_cleaning_job(job_id, identity["username"], identity["role"])
    except Exception as exc:
        raise _friendly_error(exc)


@router.post("/cleaning/jobs/{job_id}/verify")
def verify_job(
    job_id: int,
    identity: dict[str, str] = Depends(_identity),
) -> dict[str, Any]:
    """Record verification request for a cleaning job."""

    _require(identity, "view_issues")
    try:
        return verify_cleaning_job(job_id, identity["username"], identity["role"])
    except Exception as exc:
        raise _friendly_error(exc)


@router.patch("/issues/{issue_id}/status")
def patch_issue_status(
    issue_id: int,
    payload: dict[str, Any],
    identity: dict[str, str] = Depends(_identity),
) -> dict[str, Any]:
    """Update issue lifecycle status."""

    target_status = str(payload.get("status", "")).upper()
    if target_status == "FALSE_POSITIVE":
        _require(identity, "mark_false_positive")
    elif target_status == "IGNORED":
        _require(identity, "ignore_issue")
    elif target_status == "RESOLVED":
        _require(identity, "resolve_issue")
    elif target_status == "ASSIGNED":
        _require(identity, "assign_issues")
    else:
        _require(identity, "update_issue_status")
    try:
        if target_status != "ASSIGNED":
            _ensure_issue_access(issue_id, identity)
        return update_issue_status(
            issue_id=issue_id,
            status=target_status,
            updated_by=identity["username"],
            notes=payload.get("notes"),
            assigned_to=payload.get("assigned_to"),
            resolution_type=payload.get("resolution_type"),
            role=identity["role"],
        )
    except Exception as exc:
        raise _friendly_error(exc)


def _client_ip(request: Request) -> str | None:
    if request.client is None:
        return None
    return request.client.host
