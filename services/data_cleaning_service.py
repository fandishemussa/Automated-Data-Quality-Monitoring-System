"""Safe data issue remediation and data cleaning service."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from sqlalchemy import text

from data_sources.postgres_connector import (
    _quote_identifier,
    create_monitor_engine,
    create_source_engine,
    get_table_columns,
    get_table_names,
)
from services.data_cleaning_policy import (
    can_execute_without_approval,
    is_action_allowed,
    is_high_risk_action,
    load_data_cleaning_policy,
)
from utils.audit_logger import log_audit_event
from utils.logger import get_logger


logger = get_logger(__name__)

ISSUE_STATUSES = {
    "OPEN",
    "ASSIGNED",
    "IN_REVIEW",
    "FIX_PROPOSED",
    "FIX_APPLIED",
    "FALSE_POSITIVE",
    "IGNORED",
    "RESOLVED",
}

JOB_STATUSES = {
    "PENDING_APPROVAL",
    "READY_FOR_EXECUTION",
    "APPROVED",
    "EXECUTED",
    "FAILED",
    "ROLLED_BACK",
}

NON_UPDATE_ACTIONS = {
    "assign_to_owner",
    "mark_as_exception",
    "mark_as_false_positive",
    "flag_duplicate",
}


@dataclass(frozen=True)
class CleaningPayload:
    """Normalized cleaning action request."""

    issue_id: int
    action: str
    target_table: str
    target_column: str | None = None
    row_identifier: str | None = None
    new_value: Any | None = None
    parameters: dict[str, Any] | None = None
    dry_run: bool = True


def get_cleanable_issues(
    run_id: int | None = None,
    dataset_name: str | None = None,
    status: str | None = None,
    severity: str | None = None,
    assigned_to: str | None = None,
) -> list[dict[str, Any]]:
    """Return issue details enriched with latest issue status."""

    conditions: list[str] = []
    params: dict[str, Any] = {}
    if run_id is not None:
        conditions.append("i.run_id = :run_id")
        params["run_id"] = run_id
    if dataset_name:
        conditions.append("i.dataset_name = :dataset_name")
        params["dataset_name"] = dataset_name
    if severity:
        conditions.append("r.severity = :severity")
        params["severity"] = severity
    if status:
        conditions.append("COALESCE(s.status, 'OPEN') = :issue_status")
        params["issue_status"] = status
    if assigned_to:
        conditions.append("s.assigned_to = :assigned_to")
        params["assigned_to"] = assigned_to

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    query = text(
        f"""
        SELECT
            i.*,
            r.severity,
            COALESCE(s.status, 'OPEN') AS issue_status,
            s.assigned_to,
            s.resolution_type,
            s.resolution_notes,
            s.updated_at AS issue_status_updated_at
        FROM data_quality_issue_details i
        LEFT JOIN data_quality_results r
            ON r.id = i.result_id
        LEFT JOIN (
            SELECT DISTINCT ON (issue_id)
                issue_id,
                status,
                assigned_to,
                resolution_type,
                resolution_notes,
                updated_at
            FROM data_issue_status
            ORDER BY issue_id, updated_at DESC, id DESC
        ) s
            ON s.issue_id = i.id
        {where_clause}
        ORDER BY i.id DESC
        LIMIT 1000
        """
    )

    engine = create_monitor_engine()
    with engine.begin() as connection:
        return [dict(row) for row in connection.execute(query, params).mappings().all()]


def suggest_cleaning_actions(issue: dict[str, Any]) -> list[dict[str, str]]:
    """Suggest safe remediation actions based on issue metadata."""

    check_type = str(issue.get("check_type") or "").lower()
    reason = str(issue.get("reason") or "").lower()
    column = str(issue.get("column_name") or "").lower()
    suggestions: list[tuple[str, str, str]] = []

    if "not_null" in check_type or "null" in reason:
        suggestions.extend([
            ("fill_missing_value", "LOW", "Fill missing value with an approved replacement."),
            ("mark_as_exception", "LOW", "Document accepted null as an exception."),
            ("assign_to_owner", "LOW", "Assign issue to a data owner for review."),
        ])
    elif "format" in check_type or "email" in column:
        suggestions.extend([
            ("trim_whitespace", "LOW", "Remove leading and trailing whitespace."),
            ("lowercase", "LOW", "Normalize value to lowercase."),
            ("replace_value", "MEDIUM", "Replace invalid value with an approved value."),
            ("assign_to_owner", "LOW", "Mark invalid email for manual review."),
        ])
    elif "range" in check_type:
        suggestions.extend([
            ("replace_value", "MEDIUM", "Replace out-of-range value."),
            ("cap_to_min", "MEDIUM", "Cap value to configured minimum."),
            ("cap_to_max", "MEDIUM", "Cap value to configured maximum."),
            ("mark_as_exception", "LOW", "Document accepted outlier."),
        ])
    elif "categorical" in check_type:
        suggestions.extend([
            ("map_to_allowed_value", "MEDIUM", "Map invalid category to an allowed value."),
            ("replace_value", "MEDIUM", "Replace value manually."),
            ("mark_as_exception", "LOW", "Document category exception."),
        ])
    elif "duplicate" in check_type or "unique" in check_type:
        suggestions.extend([
            ("flag_duplicate", "LOW", "Flag duplicate for manual review."),
            ("assign_to_owner", "LOW", "Assign duplicate resolution to owner."),
        ])
    elif "freshness" in check_type:
        suggestions.extend([
            ("assign_to_owner", "LOW", "Assign source delay follow-up."),
            ("mark_as_exception", "LOW", "Document source delay exception."),
        ])
    elif "referential" in check_type:
        suggestions.extend([
            ("assign_to_owner", "LOW", "Assign orphan record review."),
            ("mark_as_exception", "LOW", "Document referential exception."),
        ])
    else:
        suggestions.extend([
            ("replace_value", "MEDIUM", "Replace value after review."),
            ("assign_to_owner", "LOW", "Assign issue for manual triage."),
            ("mark_as_exception", "LOW", "Document accepted exception."),
        ])

    return [{"action": action, "risk": risk, "description": description} for action, risk, description in suggestions]


def preview_cleaning_action(payload: dict[str, Any]) -> dict[str, Any]:
    """Preview a cleaning action without updating source data."""

    normalized = _normalize_payload(payload)
    _validate_cleaning_payload(normalized)
    rows = _load_target_rows(normalized)
    preview_rows = []

    for row in rows:
        old_value = None if normalized.target_column is None else row.get(normalized.target_column)
        new_value = _compute_new_value(normalized.action, old_value, normalized.new_value, normalized.parameters or {})
        preview_rows.append({
            "row_identifier": normalized.row_identifier,
            "old_value": old_value,
            "new_value": new_value,
            "will_update": normalized.action not in NON_UPDATE_ACTIONS and normalized.target_column is not None,
        })

    max_rows = int(load_data_cleaning_policy().get("max_rows_per_job", 100))
    return {
        "issue_id": normalized.issue_id,
        "action": normalized.action,
        "target_table": normalized.target_table,
        "target_column": normalized.target_column,
        "total_rows_targeted": len(preview_rows),
        "max_rows_per_job": max_rows,
        "dry_run": True,
        "summary": (
            f"Preview {normalized.action} on {normalized.target_table}."
            f"{normalized.target_column or ''}; {len(preview_rows)} row(s) targeted."
        ),
        "preview_rows": preview_rows,
    }


def create_cleaning_job(payload: dict[str, Any], requested_by: str, role: str = "viewer") -> dict[str, Any]:
    """Create a persisted cleaning job after policy validation."""

    _ensure_cleaning_schema()
    normalized = _normalize_payload(payload)
    preview = preview_cleaning_action(payload)
    approval_required = _approval_required(normalized.action, role)
    status = "PENDING_APPROVAL" if approval_required else "READY_FOR_EXECUTION"
    issue = _get_issue(normalized.issue_id)

    query = text(
        """
        INSERT INTO data_cleaning_jobs (
            run_id,
            dataset_name,
            issue_id,
            cleaning_action,
            target_table,
            target_column,
            row_identifier,
            new_value,
            parameters,
            preview_rows,
            status,
            requested_by,
            total_rows_targeted,
            total_rows_updated,
            dry_run,
            approval_required
        )
        VALUES (
            :run_id,
            :dataset_name,
            :issue_id,
            :cleaning_action,
            :target_table,
            :target_column,
            :row_identifier,
            :new_value,
            :parameters,
            :preview_rows,
            :status,
            :requested_by,
            :total_rows_targeted,
            0,
            TRUE,
            :approval_required
        )
        RETURNING *
        """
    )
    params = {
        "run_id": issue.get("run_id"),
        "dataset_name": issue.get("dataset_name") or normalized.target_table,
        "issue_id": normalized.issue_id,
        "cleaning_action": normalized.action,
        "target_table": normalized.target_table,
        "target_column": normalized.target_column,
        "row_identifier": normalized.row_identifier,
        "new_value": None if normalized.new_value is None else str(normalized.new_value),
        "parameters": json.dumps(normalized.parameters or {}, default=str),
        "preview_rows": json.dumps(preview.get("preview_rows", []), default=str),
        "status": status,
        "requested_by": requested_by,
        "total_rows_targeted": preview["total_rows_targeted"],
        "approval_required": approval_required,
    }

    engine = create_monitor_engine()
    with engine.begin() as connection:
        job = dict(connection.execute(query, params).mappings().one())

    update_issue_status(normalized.issue_id, "FIX_PROPOSED", requested_by, notes=f"Cleaning job #{job['id']} created.")
    log_audit_event(
        "CLEANING_JOB_CREATED",
        username=requested_by,
        role=role,
        entity_type="data_cleaning_job",
        entity_id=job["id"],
        new_value=job,
    )
    return job


def list_cleaning_jobs(
    status: str | None = None,
    dataset_name: str | None = None,
    requested_by: str | None = None,
    assigned_to: str | None = None,
) -> list[dict[str, Any]]:
    """List cleaning jobs with optional filters."""

    _ensure_cleaning_schema()
    conditions: list[str] = []
    params: dict[str, Any] = {}
    if status:
        conditions.append("j.status = :status")
        params["status"] = status
    if dataset_name:
        conditions.append("j.dataset_name = :dataset_name")
        params["dataset_name"] = dataset_name
    if requested_by:
        conditions.append("j.requested_by = :requested_by")
        params["requested_by"] = requested_by
    if assigned_to:
        conditions.append("(s.assigned_to = :assigned_to OR j.requested_by = :assigned_to)")
        params["assigned_to"] = assigned_to
    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    engine = create_monitor_engine()
    with engine.begin() as connection:
        jobs = [
            dict(row)
            for row in connection.execute(
                text(
                    f"""
                    SELECT j.*
                    FROM data_cleaning_jobs j
                    LEFT JOIN (
                        SELECT DISTINCT ON (issue_id)
                            issue_id,
                            assigned_to
                        FROM data_issue_status
                        ORDER BY issue_id, updated_at DESC, id DESC
                    ) s
                        ON s.issue_id = j.issue_id
                    {where_clause}
                    ORDER BY j.id DESC
                    LIMIT 1000
                    """
                ),
                params,
            ).mappings().all()
        ]
        changes_by_job = _load_change_logs_for_jobs(connection, [int(job["id"]) for job in jobs])

    return [_decorate_job(job, changes_by_job.get(int(job["id"]), [])) for job in jobs]


def get_cleaning_job(job_id: int) -> dict[str, Any]:
    """Return one cleaning job and its change log."""

    _ensure_cleaning_schema()
    engine = create_monitor_engine()
    with engine.begin() as connection:
        job = connection.execute(
            text("SELECT * FROM data_cleaning_jobs WHERE id = :job_id"),
            {"job_id": job_id},
        ).mappings().one_or_none()
        if job is None:
            raise ValueError(f"Cleaning job {job_id} not found.")
        changes = connection.execute(
            text("SELECT * FROM data_cleaning_change_log WHERE job_id = :job_id ORDER BY id DESC"),
            {"job_id": job_id},
        ).mappings().all()

    return _decorate_job(dict(job), [dict(change) for change in changes])


def approve_cleaning_job(job_id: int, approved_by: str, role: str = "admin") -> dict[str, Any]:
    """Approve a cleaning job."""

    engine = create_monitor_engine()
    with engine.begin() as connection:
        job = connection.execute(
            text(
                """
                UPDATE data_cleaning_jobs
                SET status = 'APPROVED',
                    approved_by = :approved_by,
                    approved_at = CURRENT_TIMESTAMP
                WHERE id = :job_id
                  AND status IN ('PENDING_APPROVAL', 'READY_FOR_EXECUTION')
                RETURNING *
                """
            ),
            {"job_id": job_id, "approved_by": approved_by},
        ).mappings().one_or_none()
    if job is None:
        raise ValueError(f"Cleaning job {job_id} cannot be approved.")

    log_audit_event(
        "CLEANING_JOB_APPROVED",
        username=approved_by,
        role=role,
        entity_type="data_cleaning_job",
        entity_id=job_id,
        new_value=dict(job),
    )
    return dict(job)


def execute_cleaning_job(job_id: int, executed_by: str, role: str = "viewer") -> dict[str, Any]:
    """Execute an approved cleaning job and record before/after changes."""

    job = get_cleaning_job(job_id)
    _ensure_job_executable(job, role)
    payload = {
        "issue_id": job["issue_id"],
        "action": job["cleaning_action"],
        "target_table": job["target_table"],
        "target_column": job["target_column"],
        "row_identifier": job.get("row_identifier"),
        "new_value": job.get("new_value"),
        "parameters": _loads_json(job.get("parameters")),
    }
    normalized = _normalize_payload(payload)
    preview = preview_cleaning_action(payload)

    if preview["total_rows_targeted"] > int(load_data_cleaning_policy().get("max_rows_per_job", 100)):
        raise ValueError("Cleaning job exceeds max_rows_per_job policy.")

    updated = 0
    try:
        if normalized.action not in NON_UPDATE_ACTIONS and normalized.target_column:
            rows = _load_target_rows(normalized)
            pending_changes: list[tuple[Any, Any]] = []
            for row in rows:
                old_value = row.get(normalized.target_column)
                new_value = _compute_new_value(
                    normalized.action,
                    old_value,
                    normalized.new_value,
                    normalized.parameters or {},
                )
                pending_changes.append((old_value, new_value))

            distinct_new_values = {
                json.dumps(new_value, sort_keys=True, default=str)
                for _, new_value in pending_changes
            }
            if len(distinct_new_values) > 1:
                raise ValueError(
                    "This cleaning job produces different replacement values across rows. "
                    "Create separate jobs so each source update remains auditable."
                )

            for old_value, new_value in pending_changes:
                _record_change(job, normalized, old_value, new_value)

            table_identifier = _quote_identifier(normalized.target_table, "table name")
            column_identifier = _quote_identifier(normalized.target_column, "column name")
            where = parse_row_identifier(str(normalized.row_identifier or ""))
            where_clause = " AND ".join([
                f"{_quote_identifier(column, 'column name')} = :where_{column}"
                for column in where.keys()
            ])
            update_query = text(
                f"UPDATE {table_identifier} SET {column_identifier} = :new_value WHERE {where_clause}"
            )
            params = {"new_value": pending_changes[0][1] if pending_changes else None}
            params.update({f"where_{column}": value for column, value in where.items()})
            source_engine = create_source_engine()
            with source_engine.begin() as source_connection:
                result = source_connection.execute(update_query, params)
                updated = int(result.rowcount or 0)

        _mark_job_executed(job_id, executed_by, updated)
        update_issue_status(int(job["issue_id"]), "FIX_APPLIED", executed_by, notes=f"Cleaning job #{job_id} executed.")
        event_type = "CLEANING_JOB_EXECUTED"
    except Exception as exc:
        _mark_job_failed(job_id, str(exc))
        event_type = "CLEANING_JOB_FAILED"
        log_audit_event(
            event_type,
            username=executed_by,
            role=role,
            entity_type="data_cleaning_job",
            entity_id=job_id,
            new_value={"error": str(exc)},
        )
        raise

    result_job = get_cleaning_job(job_id)
    log_audit_event(
        event_type,
        username=executed_by,
        role=role,
        entity_type="data_cleaning_job",
        entity_id=job_id,
        new_value={"updated": updated, "job": result_job},
    )
    return result_job


def update_issue_status(
    issue_id: int,
    status: str,
    updated_by: str,
    notes: str | None = None,
    assigned_to: str | None = None,
    resolution_type: str | None = None,
    role: str | None = None,
) -> dict[str, Any]:
    """Record an issue lifecycle status update."""

    normalized_status = status.upper()
    if normalized_status not in ISSUE_STATUSES:
        raise ValueError(f"Unsupported issue status: {status}")
    issue = _get_issue(issue_id)
    latest_status = _get_latest_issue_status(issue_id)
    effective_assigned_to = assigned_to if assigned_to is not None else latest_status.get("assigned_to")
    engine = create_monitor_engine()
    with engine.begin() as connection:
        row = connection.execute(
            text(
                """
                INSERT INTO data_issue_status (
                    issue_id,
                    run_id,
                    dataset_name,
                    status,
                    assigned_to,
                    resolution_type,
                    resolution_notes,
                    updated_by
                )
                VALUES (
                    :issue_id,
                    :run_id,
                    :dataset_name,
                    :status,
                    :assigned_to,
                    :resolution_type,
                    :resolution_notes,
                    :updated_by
                )
                RETURNING *
                """
            ),
            {
                "issue_id": issue_id,
                "run_id": issue.get("run_id"),
                "dataset_name": issue.get("dataset_name"),
                "status": normalized_status,
                "assigned_to": effective_assigned_to,
                "resolution_type": resolution_type,
                "resolution_notes": notes,
                "updated_by": updated_by,
            },
        ).mappings().one()
    event_type = {
        "FALSE_POSITIVE": "ISSUE_MARKED_FALSE_POSITIVE",
        "IGNORED": "ISSUE_IGNORED",
        "RESOLVED": "ISSUE_RESOLVED",
    }.get(normalized_status, "ISSUE_STATUS_UPDATED")
    log_audit_event(
        event_type,
        username=updated_by,
        role=role,
        entity_type="data_quality_issue",
        entity_id=issue_id,
        new_value=dict(row),
    )
    if normalized_status in {"FIX_APPLIED", "FALSE_POSITIVE", "IGNORED", "RESOLVED"}:
        _resolve_alerts_for_fixed_issue(issue, updated_by, role)
    return dict(row)


def rollback_cleaning_job(job_id: int, requested_by: str, role: str = "admin") -> dict[str, Any]:
    """Rollback a cleaning job using recorded old values."""

    job = get_cleaning_job(job_id)
    if job["status"] != "EXECUTED":
        raise ValueError("Only EXECUTED jobs can be rolled back.")
    if not job.get("change_log"):
        raise ValueError("No change log exists for rollback.")

    source_engine = create_source_engine()
    with source_engine.begin() as connection:
        for change in job["change_log"]:
            table_identifier = _quote_identifier(change["table_name"], "table name")
            column_identifier = _quote_identifier(change["column_name"], "column name")
            where = parse_row_identifier(change["row_identifier"])
            where_clause = " AND ".join([
                f"{_quote_identifier(column, 'column name')} = :where_{column}"
                for column in where.keys()
            ])
            query = text(f"UPDATE {table_identifier} SET {column_identifier} = :old_value WHERE {where_clause}")
            params = {"old_value": change["old_value"]}
            params.update({f"where_{column}": value for column, value in where.items()})
            connection.execute(query, params)

    engine = create_monitor_engine()
    with engine.begin() as connection:
        row = connection.execute(
            text(
                """
                UPDATE data_cleaning_jobs
                SET status = 'ROLLED_BACK'
                WHERE id = :job_id
                RETURNING *
                """
            ),
            {"job_id": job_id},
        ).mappings().one()
    log_audit_event(
        "CLEANING_JOB_ROLLED_BACK",
        username=requested_by,
        role=role,
        entity_type="data_cleaning_job",
        entity_id=job_id,
        new_value=dict(row),
    )
    return dict(row)


def verify_cleaning_job(job_id: int, requested_by: str, role: str = "viewer") -> dict[str, Any]:
    """Record a verification request for a cleaning job."""

    job = get_cleaning_job(job_id)
    result = {
        "job_id": job_id,
        "status": "VERIFICATION_REQUIRES_RERUN",
        "message": "Run checks again and compare latest issue details to confirm remediation.",
    }
    log_audit_event(
        "CLEANING_VERIFIED",
        username=requested_by,
        role=role,
        entity_type="data_cleaning_job",
        entity_id=job_id,
        new_value=result,
    )
    return result


def parse_row_identifier(row_identifier: str) -> dict[str, Any]:
    """Parse supported row identifier formats into equality predicates."""

    text_value = str(row_identifier or "").strip()
    if not text_value:
        raise ValueError("row_identifier is required.")

    if text_value.startswith("{"):
        loaded = json.loads(text_value)
        if not isinstance(loaded, dict) or not loaded:
            raise ValueError("row_identifier JSON must be a non-empty object.")
        return loaded

    if "=" in text_value:
        key, value = text_value.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'\"")
        _quote_identifier(key, "row identifier column")
        return {key: value}

    if ":" in text_value:
        key, value = text_value.split(":", 1)
        key = key.strip()
        value = value.strip().strip("'\"")
        _quote_identifier(key, "row identifier column")
        return {key: value}

    raise ValueError("row_identifier must be JSON or use column=value format.")


def build_change_log_payload(
    job_id: int,
    dataset_name: str,
    table_name: str,
    column_name: str,
    row_identifier: str,
    old_value: Any,
    new_value: Any,
    change_reason: str,
) -> dict[str, Any]:
    """Build a normalized change-log payload."""

    return {
        "job_id": job_id,
        "dataset_name": dataset_name,
        "table_name": table_name,
        "column_name": column_name,
        "row_identifier": row_identifier,
        "old_value": None if old_value is None else str(old_value),
        "new_value": None if new_value is None else str(new_value),
        "change_reason": change_reason,
    }


def build_proposed_change_rows(job: dict[str, Any]) -> list[dict[str, Any]]:
    """Return preview rows normalized for admin review before approval."""

    rows = _loads_json_list(job.get("preview_rows"))
    proposed = []
    for row in rows:
        proposed.append({
            "job_id": job.get("id"),
            "dataset_name": job.get("dataset_name"),
            "table_name": job.get("target_table"),
            "column_name": job.get("target_column"),
            "row_identifier": row.get("row_identifier") or job.get("row_identifier"),
            "old_value": None if row.get("old_value") is None else str(row.get("old_value")),
            "new_value": None if row.get("new_value") is None else str(row.get("new_value")),
            "change_reason": f"PROPOSED_{job.get('cleaning_action')}",
            "will_update": bool(row.get("will_update")),
        })
    return proposed


def _normalize_payload(payload: dict[str, Any]) -> CleaningPayload:
    return CleaningPayload(
        issue_id=int(payload["issue_id"]),
        action=str(payload.get("action") or payload.get("cleaning_action") or "").strip(),
        target_table=str(payload.get("target_table") or "").strip(),
        target_column=str(payload.get("target_column") or "").strip() or None,
        row_identifier=str(payload.get("row_identifier") or "").strip() or None,
        new_value=payload.get("new_value"),
        parameters=payload.get("parameters") if isinstance(payload.get("parameters"), dict) else {},
        dry_run=bool(payload.get("dry_run", True)),
    )


def _validate_cleaning_payload(payload: CleaningPayload) -> None:
    policy = load_data_cleaning_policy()
    if not policy.get("enabled", True):
        raise ValueError("Data cleaning is disabled by policy.")
    if not is_action_allowed(payload.action):
        raise ValueError(f"Cleaning action is not allowed: {payload.action}")
    if not payload.target_table:
        raise ValueError("target_table is required.")
    if payload.action not in NON_UPDATE_ACTIONS and not payload.target_column:
        raise ValueError("target_column is required for this cleaning action.")
    if payload.target_table not in get_table_names():
        raise ValueError(f"Target table is not allowed or does not exist: {payload.target_table}")
    if payload.target_column and payload.target_column not in get_table_columns(payload.target_table):
        raise ValueError(f"Target column does not exist on {payload.target_table}: {payload.target_column}")
    if payload.row_identifier:
        where = parse_row_identifier(payload.row_identifier)
        columns = get_table_columns(payload.target_table)
        invalid = [column for column in where.keys() if column not in columns]
        if invalid:
            raise ValueError(f"Row identifier column(s) do not exist: {', '.join(invalid)}")


def _load_target_rows(payload: CleaningPayload) -> list[dict[str, Any]]:
    if not payload.row_identifier:
        return []
    table_identifier = _quote_identifier(payload.target_table, "table name")
    where = parse_row_identifier(payload.row_identifier)
    where_clause = " AND ".join([
        f"{_quote_identifier(column, 'column name')} = :where_{column}"
        for column in where.keys()
    ])
    query = text(f"SELECT * FROM {table_identifier} WHERE {where_clause} LIMIT :limit")
    params = {f"where_{column}": value for column, value in where.items()}
    params["limit"] = int(load_data_cleaning_policy().get("max_rows_per_job", 100))
    source_engine = create_source_engine()
    with source_engine.begin() as connection:
        return [dict(row) for row in connection.execute(query, params).mappings().all()]


def _compute_new_value(action: str, old_value: Any, new_value: Any, parameters: dict[str, Any]) -> Any:
    if action in {"fill_missing_value", "replace_value", "map_to_allowed_value"}:
        return new_value
    if action == "trim_whitespace":
        return None if old_value is None else str(old_value).strip()
    if action == "lowercase":
        return None if old_value is None else str(old_value).lower()
    if action == "uppercase":
        return None if old_value is None else str(old_value).upper()
    if action == "regex_replace":
        pattern = str(parameters.get("pattern", ""))
        replacement = str(parameters.get("replacement", ""))
        return None if old_value is None else re.sub(pattern, replacement, str(old_value))
    if action == "cap_to_min":
        minimum = float(parameters.get("min", new_value))
        return max(float(old_value), minimum)
    if action == "cap_to_max":
        maximum = float(parameters.get("max", new_value))
        return min(float(old_value), maximum)
    return old_value


def _approval_required(action: str, role: str) -> bool:
    policy = load_data_cleaning_policy()
    if policy.get("require_approval_for_all", False):
        return True
    if is_high_risk_action(action):
        return True
    return not can_execute_without_approval(role)


def _get_issue(issue_id: int) -> dict[str, Any]:
    engine = create_monitor_engine()
    with engine.begin() as connection:
        issue = connection.execute(
            text("SELECT * FROM data_quality_issue_details WHERE id = :issue_id"),
            {"issue_id": issue_id},
        ).mappings().one_or_none()
    if issue is None:
        raise ValueError(f"Issue {issue_id} not found.")
    return dict(issue)


def _get_latest_issue_status(issue_id: int) -> dict[str, Any]:
    """Return the latest issue status row, or an empty mapping when none exists."""

    engine = create_monitor_engine()
    with engine.begin() as connection:
        row = connection.execute(
            text(
                """
                SELECT *
                FROM data_issue_status
                WHERE issue_id = :issue_id
                ORDER BY updated_at DESC, id DESC
                LIMIT 1
                """
            ),
            {"issue_id": issue_id},
        ).mappings().one_or_none()
    return dict(row) if row is not None else {}


def _ensure_job_executable(job: dict[str, Any], role: str) -> None:
    policy = load_data_cleaning_policy()
    if not policy.get("allow_source_updates", False):
        raise ValueError("Source updates are disabled by data cleaning policy.")
    if job["status"] not in {"APPROVED", "READY_FOR_EXECUTION"}:
        raise ValueError("Cleaning job is not approved or ready for execution.")
    if role not in {"admin", "analyst", "data_analyst", "data_engineer"}:
        raise PermissionError("Viewer role cannot execute cleaning jobs.")
    if role in {"analyst", "data_analyst", "data_engineer"} and job.get("approval_required") and job["status"] != "APPROVED":
        raise PermissionError("Analysts can execute approved jobs only.")


def _record_change(job: dict[str, Any], payload: CleaningPayload, old_value: Any, new_value: Any) -> None:
    params = build_change_log_payload(
        job_id=int(job["id"]),
        dataset_name=str(job.get("dataset_name") or payload.target_table),
        table_name=payload.target_table,
        column_name=str(payload.target_column),
        row_identifier=str(payload.row_identifier),
        old_value=old_value,
        new_value=new_value,
        change_reason=payload.action,
    )
    engine = create_monitor_engine()
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO data_cleaning_change_log (
                    job_id,
                    dataset_name,
                    table_name,
                    column_name,
                    row_identifier,
                    old_value,
                    new_value,
                    change_reason
                )
                VALUES (
                    :job_id,
                    :dataset_name,
                    :table_name,
                    :column_name,
                    :row_identifier,
                    :old_value,
                    :new_value,
                    :change_reason
                )
                """
            ),
            params,
        )


def _resolve_alerts_for_fixed_issue(issue: dict[str, Any], updated_by: str, role: str | None = None) -> None:
    """Resolve related alerts when the underlying issue set is fully closed."""

    run_id = issue.get("run_id")
    dataset_name = str(issue.get("dataset_name") or "").strip()
    if not run_id:
        return

    engine = create_monitor_engine()
    with engine.begin() as connection:
        _ensure_alert_resolution_columns(connection)
        dataset_open_count = _open_issue_count(connection, run_id=run_id, dataset_name=dataset_name)
        run_open_count = _open_issue_count(connection, run_id=run_id, dataset_name=None)

        resolved_rows = []
        if dataset_name and dataset_open_count == 0:
            resolved_rows.extend(
                connection.execute(
                    text(
                        """
                        UPDATE data_quality_alerts
                        SET
                            is_resolved = TRUE,
                            resolved_at = CURRENT_TIMESTAMP,
                            resolved_by = :updated_by,
                            escalation_status = COALESCE(escalation_status, 'RESOLVED'),
                            resolution_notes = TRIM(BOTH ' ' FROM CONCAT(
                                COALESCE(resolution_notes, ''),
                                ' Auto-resolved because all open issues for dataset ',
                                :dataset_name,
                                ' are closed.'
                            ))
                        WHERE run_id = :run_id
                          AND COALESCE(is_resolved, FALSE) = FALSE
                          AND LOWER(COALESCE(message, '')) LIKE :dataset_pattern
                        RETURNING id
                        """
                    ),
                    {
                        "run_id": run_id,
                        "dataset_name": dataset_name,
                        "dataset_pattern": f"%{dataset_name.lower()}%",
                        "updated_by": updated_by,
                    },
                ).mappings().all()
            )

        if run_open_count == 0:
            resolved_rows.extend(
                connection.execute(
                    text(
                        """
                        UPDATE data_quality_alerts
                        SET
                            is_resolved = TRUE,
                            resolved_at = CURRENT_TIMESTAMP,
                            resolved_by = :updated_by,
                            escalation_status = COALESCE(escalation_status, 'RESOLVED'),
                            resolution_notes = TRIM(BOTH ' ' FROM CONCAT(
                                COALESCE(resolution_notes, ''),
                                ' Auto-resolved because all open issues for run ',
                                :run_id,
                                ' are closed.'
                            ))
                        WHERE run_id = :run_id
                          AND COALESCE(is_resolved, FALSE) = FALSE
                          AND alert_type IN (
                              'CRITICAL_DATA_QUALITY_ISSUE',
                              'DATA_QUALITY_FAILURE',
                              'LOW_QUALITY_SCORE'
                          )
                        RETURNING id
                        """
                    ),
                    {"run_id": run_id, "updated_by": updated_by},
                ).mappings().all()
            )

    if resolved_rows:
        log_audit_event(
            "ALERT_AUTO_RESOLVED_FROM_ISSUE",
            username=updated_by,
            role=role,
            entity_type="data_quality_issue",
            entity_id=issue.get("id"),
            new_value={
                "run_id": run_id,
                "dataset_name": dataset_name,
                "alert_ids": [row["id"] for row in resolved_rows],
            },
        )


def _open_issue_count(connection, run_id: int, dataset_name: str | None) -> int:
    conditions = ["i.run_id = :run_id"]
    params: dict[str, Any] = {"run_id": run_id}
    if dataset_name:
        conditions.append("i.dataset_name = :dataset_name")
        params["dataset_name"] = dataset_name

    return int(
        connection.execute(
            text(
                f"""
                SELECT COUNT(*)
                FROM data_quality_issue_details i
                LEFT JOIN (
                    SELECT DISTINCT ON (issue_id)
                        issue_id,
                        status
                    FROM data_issue_status
                    ORDER BY issue_id, updated_at DESC, id DESC
                ) s
                    ON s.issue_id = i.id
                WHERE {' AND '.join(conditions)}
                  AND COALESCE(s.status, 'OPEN') NOT IN (
                      'FIX_APPLIED',
                      'FALSE_POSITIVE',
                      'IGNORED',
                      'RESOLVED'
                  )
                """
            ),
            params,
        ).scalar_one()
    )


def _ensure_alert_resolution_columns(connection) -> None:
    for statement in [
        "ALTER TABLE IF EXISTS data_quality_alerts ADD COLUMN IF NOT EXISTS resolved_by VARCHAR(255)",
        "ALTER TABLE IF EXISTS data_quality_alerts ADD COLUMN IF NOT EXISTS resolved_at TIMESTAMP",
        "ALTER TABLE IF EXISTS data_quality_alerts ADD COLUMN IF NOT EXISTS resolution_notes TEXT",
        "ALTER TABLE IF EXISTS data_quality_alerts ADD COLUMN IF NOT EXISTS escalation_status VARCHAR(50)",
    ]:
        connection.execute(text(statement))


def _ensure_cleaning_schema() -> None:
    """Apply small backward-compatible remediation table migrations."""

    engine = create_monitor_engine()
    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE IF EXISTS data_cleaning_jobs ADD COLUMN IF NOT EXISTS preview_rows TEXT"))


def _load_change_logs_for_jobs(connection, job_ids: list[int]) -> dict[int, list[dict[str, Any]]]:
    """Load executed change logs for job list responses."""

    if not job_ids:
        return {}

    rows = connection.execute(
        text(
            """
            SELECT *
            FROM data_cleaning_change_log
            WHERE job_id = ANY(:job_ids)
            ORDER BY id DESC
            """
        ),
        {"job_ids": job_ids},
    ).mappings().all()
    grouped: dict[int, list[dict[str, Any]]] = {}
    for row in rows:
        change = dict(row)
        grouped.setdefault(int(change["job_id"]), []).append(change)
    return grouped


def _decorate_job(job: dict[str, Any], change_log: list[dict[str, Any]]) -> dict[str, Any]:
    """Attach proposed and executed change records to a cleaning job."""

    decorated = dict(job)
    decorated["proposed_changes"] = build_proposed_change_rows(decorated)
    decorated["change_log"] = change_log
    return decorated


def _mark_job_executed(job_id: int, executed_by: str, updated: int) -> None:
    engine = create_monitor_engine()
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                UPDATE data_cleaning_jobs
                SET status = 'EXECUTED',
                    executed_by = :executed_by,
                    executed_at = CURRENT_TIMESTAMP,
                    total_rows_updated = :updated,
                    dry_run = FALSE,
                    error_message = NULL
                WHERE id = :job_id
                """
            ),
            {"job_id": job_id, "executed_by": executed_by, "updated": updated},
        )


def _mark_job_failed(job_id: int, error: str) -> None:
    engine = create_monitor_engine()
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                UPDATE data_cleaning_jobs
                SET status = 'FAILED',
                    error_message = :error
                WHERE id = :job_id
                """
            ),
            {"job_id": job_id, "error": error},
        )


def _loads_json(value: Any) -> dict[str, Any]:
    if not value:
        return {}
    if isinstance(value, dict):
        return value
    try:
        loaded = json.loads(str(value))
        return loaded if isinstance(loaded, dict) else {}
    except json.JSONDecodeError:
        return {}


def _loads_json_list(value: Any) -> list[dict[str, Any]]:
    if not value:
        return []
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    try:
        loaded = json.loads(str(value))
        return [item for item in loaded if isinstance(item, dict)] if isinstance(loaded, list) else []
    except json.JSONDecodeError:
        return []
