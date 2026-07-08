"""Enterprise alert escalation workflow."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

import pandas as pd
from sqlalchemy import text

from alerts.ownership import load_alert_ownership_rules
from data_sources.postgres_connector import create_monitor_engine
from notifications.mailtrap_notifier import send_mailtrap_alert_email
from notifications.slack_notifier import send_slack_alert
from notifications.teams_notifier import send_teams_alert
from utils.audit_logger import log_audit_event
from utils.logger import get_logger


logger = get_logger(__name__)

ESCALATABLE_SEVERITIES = {"CRITICAL", "HIGH"}
DEFAULT_ESCALATION_RULES = {
    "CRITICAL": {"after_hours": 4, "escalation_level": 1, "notify_team": "Data Platform"},
    "HIGH": {"after_hours": 24, "escalation_level": 1, "notify_team": "Data Governance"},
}


def calculate_sla_due_at(
    created_at: datetime | str | pd.Timestamp,
    severity: str,
    escalation_rules: dict[str, Any] | None = None,
) -> datetime:
    """Calculate the escalation due time for an alert severity."""

    created = _to_datetime(created_at)
    rules = escalation_rules or _load_escalation_rules()
    severity_rule = rules.get(str(severity or "").upper(), {})
    after_hours = _safe_float(severity_rule.get("after_hours"), 24)
    return created + timedelta(hours=after_hours)


def find_alerts_to_escalate(
    now: datetime | None = None,
    escalation_rules: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Find unresolved CRITICAL/HIGH alerts that are past their SLA due time."""

    now = now or datetime.now()
    rules = escalation_rules or _load_escalation_rules()
    _ensure_escalation_columns()
    query = text(
        """
        SELECT *
        FROM data_quality_alerts
        WHERE COALESCE(is_resolved, FALSE) = FALSE
          AND UPPER(COALESCE(severity, '')) IN ('CRITICAL', 'HIGH')
          AND UPPER(COALESCE(escalation_status, '')) NOT IN ('ESCALATED')
        ORDER BY created_at ASC, id ASC
        """
    )

    try:
        engine = create_monitor_engine()
        with engine.begin() as connection:
            rows = connection.execute(query).mappings().all()
    except Exception:
        logger.exception("Could not load alerts for escalation.")
        return []

    due_alerts = []
    for row in rows:
        alert = dict(row)
        due_at = alert.get("sla_due_at") or calculate_sla_due_at(
            alert.get("created_at"),
            alert.get("severity"),
            rules,
        )
        due_at = _to_datetime(due_at)
        if due_at <= now:
            alert["sla_due_at"] = due_at
            due_alerts.append(alert)

    return due_alerts


def escalate_alert(
    alert_id: int,
    escalation_status: str = "ESCALATED",
    escalation_level: int = 1,
    sla_due_at: datetime | None = None,
) -> bool:
    """Mark one alert as escalated."""

    _ensure_escalation_columns()
    query = text(
        """
        UPDATE data_quality_alerts
        SET
            escalation_status = :escalation_status,
            escalation_level = :escalation_level,
            escalated_at = CURRENT_TIMESTAMP,
            sla_due_at = COALESCE(:sla_due_at, sla_due_at)
        WHERE id = :alert_id
          AND COALESCE(is_resolved, FALSE) = FALSE
        """
    )

    engine = create_monitor_engine()
    with engine.begin() as connection:
        result = connection.execute(
            query,
            {
                "alert_id": int(alert_id),
                "escalation_status": escalation_status,
                "escalation_level": int(escalation_level),
                "sla_due_at": sla_due_at,
            },
        )

    updated = result.rowcount > 0
    if updated:
        log_audit_event(
            "ALERT_ESCALATED",
            entity_type="alert",
            entity_id=str(alert_id),
            new_value={
                "escalation_status": escalation_status,
                "escalation_level": escalation_level,
                "sla_due_at": str(sla_due_at) if sla_due_at else None,
            },
        )
    return updated


def run_alert_escalation(now: datetime | None = None) -> list[dict[str, Any]]:
    """Escalate all unresolved due alerts and send optional notifications."""

    rules = _load_escalation_rules()
    due_alerts = find_alerts_to_escalate(now=now, escalation_rules=rules)
    escalated = []

    for alert in due_alerts:
        severity = str(alert.get("severity", "")).upper()
        severity_rule = rules.get(severity, {})
        escalation_level = int(severity_rule.get("escalation_level", 1))
        notify_team = severity_rule.get("notify_team", "")
        updated = escalate_alert(
            alert_id=int(alert["id"]),
            escalation_status="ESCALATED",
            escalation_level=escalation_level,
            sla_due_at=_to_datetime(alert["sla_due_at"]),
        )
        if not updated:
            continue
        escalated_alert = {
            **alert,
            "escalation_status": "ESCALATED",
            "escalation_level": escalation_level,
            "notify_team": notify_team,
            "message": f"[ESCALATED to {notify_team or 'configured owner'}] {alert.get('message', '')}",
        }
        escalated.append(escalated_alert)

    if escalated:
        _send_escalation_notifications(escalated)

    logger.info("Escalated %s alert(s).", len(escalated))
    return escalated


def is_alert_due_for_escalation(
    alert: dict[str, Any],
    now: datetime,
    escalation_rules: dict[str, Any] | None = None,
) -> bool:
    """Return whether one alert should be escalated."""

    if _is_truthy(alert.get("is_resolved")):
        return False
    severity = str(alert.get("severity", "")).upper()
    if severity not in ESCALATABLE_SEVERITIES:
        return False
    if str(alert.get("escalation_status", "")).upper() == "ESCALATED":
        return False
    due_at = alert.get("sla_due_at") or calculate_sla_due_at(
        alert.get("created_at"),
        severity,
        escalation_rules,
    )
    return _to_datetime(due_at) <= now


def _send_escalation_notifications(alerts: list[dict[str, Any]]) -> None:
    """Send optional Slack/Teams/email notifications for escalated alerts."""

    run_id = int(alerts[0].get("run_id") or 0)
    summary = {
        "overall_status": "ESCALATED",
        "quality_score": "N/A",
        "total_checks": "N/A",
        "failed_checks": len(alerts),
        "critical_checks": sum(1 for alert in alerts if str(alert.get("severity")).upper() == "CRITICAL"),
    }

    try:
        send_slack_alert(run_id, summary, alerts)
        send_teams_alert(run_id, summary, alerts)
        send_mailtrap_alert_email(run_id, summary, alerts)
    except Exception:
        logger.exception("Escalation notification attempt failed.")


def _load_escalation_rules() -> dict[str, Any]:
    """Load escalation config from alert ownership rules."""

    ownership_rules = load_alert_ownership_rules()
    configured = ownership_rules.get("escalation", {})
    if not isinstance(configured, dict):
        return DEFAULT_ESCALATION_RULES
    return {**DEFAULT_ESCALATION_RULES, **configured}


def _ensure_escalation_columns() -> None:
    """Ensure alert escalation columns are available."""

    statements = [
        "ALTER TABLE IF EXISTS data_quality_alerts ADD COLUMN IF NOT EXISTS sla_due_at TIMESTAMP",
        "ALTER TABLE IF EXISTS data_quality_alerts ADD COLUMN IF NOT EXISTS escalation_status VARCHAR(50)",
        "ALTER TABLE IF EXISTS data_quality_alerts ADD COLUMN IF NOT EXISTS escalated_at TIMESTAMP",
        "ALTER TABLE IF EXISTS data_quality_alerts ADD COLUMN IF NOT EXISTS escalation_level INT",
    ]
    engine = create_monitor_engine()
    with engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))


def _to_datetime(value: datetime | str | pd.Timestamp | None) -> datetime:
    """Convert database/YAML time values to datetime."""

    if value is None:
        return datetime.now()
    if isinstance(value, datetime):
        return value.replace(tzinfo=None)
    parsed = pd.to_datetime(value, errors="coerce")
    if pd.isna(parsed):
        return datetime.now()
    return parsed.to_pydatetime().replace(tzinfo=None)


def _safe_float(value: Any, default: float) -> float:
    """Parse a float with fallback."""

    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _is_truthy(value: Any) -> bool:
    """Return truthiness for database booleans and string flags."""

    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "on"}
    return bool(value)
