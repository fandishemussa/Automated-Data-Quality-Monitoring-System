from typing import Any

from sqlalchemy import text

from alerts.ownership import determine_alert_owner, load_alert_ownership_rules
from data_sources.postgres_connector import create_monitor_engine
from utils.logger import get_logger


logger = get_logger(__name__)


def create_alerts_for_run(
    run_id: int,
    summary: dict[str, Any],
    results: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Create alert records for a completed data quality run."""

    logger.info("Evaluating alerts for run %s.", run_id)

    alerts = []
    ownership_rules = load_alert_ownership_rules()

    critical_checks = summary.get("critical_checks", 0)
    failed_checks = summary.get("failed_checks", 0)
    quality_score = summary.get("quality_score", 0)

    if critical_checks > 0:
        alerts.append({
            "run_id": run_id,
            "alert_type": "CRITICAL_DATA_QUALITY_ISSUE",
            "severity": "CRITICAL",
            "message": f"Run {run_id} has {critical_checks} critical data quality issue(s).",
        })

    if failed_checks > 0:
        alerts.append({
            "run_id": run_id,
            "alert_type": "DATA_QUALITY_FAILURE",
            "severity": "HIGH",
            "message": f"Run {run_id} has {failed_checks} failed data quality check(s).",
        })

    if quality_score < 75:
        alerts.append({
            "run_id": run_id,
            "alert_type": "LOW_QUALITY_SCORE",
            "severity": "MEDIUM",
            "message": f"Run {run_id} quality score is low: {quality_score}%.",
        })

    alerts.extend(_build_dataset_alerts(run_id, results or []))
    alerts = [
        _with_owner(alert, ownership_rules)
        for alert in _deduplicate_alerts(alerts)
    ]

    if not alerts:
        logger.info("No alerts created for run %s. Data quality looks good.", run_id)
        return []

    engine = create_monitor_engine()

    insert_query = text("""
        INSERT INTO data_quality_alerts (
            run_id,
            alert_type,
            severity,
            message,
            owner_team,
            owner_email,
            assigned_to,
            resolution_notes
        )
        VALUES (
            :run_id,
            :alert_type,
            :severity,
            :message,
            :owner_team,
            :owner_email,
            :assigned_to,
            :resolution_notes
        )
    """)

    with engine.begin() as connection:
        _ensure_alert_table_schema(connection)

        for alert in alerts:
            connection.execute(insert_query, _alert_insert_params(alert))
            logger.warning(
                "Created %s alert for run %s: %s",
                alert["severity"],
                run_id,
                alert["message"],
            )

    logger.info("%s alert(s) created for run %s.", len(alerts), run_id)
    return alerts


def _ensure_alert_table_schema(connection) -> None:
    """Ensure alert ownership columns exist before inserting alerts."""

    statements = [
        """
        CREATE TABLE IF NOT EXISTS data_quality_alerts (
            id SERIAL PRIMARY KEY,
            run_id INT,
            alert_type VARCHAR(100),
            severity VARCHAR(20),
            message TEXT,
            owner_team VARCHAR(100),
            owner_email VARCHAR(255),
            assigned_to VARCHAR(255),
            resolution_notes TEXT,
            resolved_by VARCHAR(255),
            is_resolved BOOLEAN DEFAULT FALSE,
            resolved_at TIMESTAMP,
            sla_due_at TIMESTAMP,
            escalation_status VARCHAR(50),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        ALTER TABLE IF EXISTS data_quality_alerts
        ADD COLUMN IF NOT EXISTS owner_team VARCHAR(100)
        """,
        """
        ALTER TABLE IF EXISTS data_quality_alerts
        ADD COLUMN IF NOT EXISTS owner_email VARCHAR(255)
        """,
        """
        ALTER TABLE IF EXISTS data_quality_alerts
        ADD COLUMN IF NOT EXISTS assigned_to VARCHAR(255)
        """,
        """
        ALTER TABLE IF EXISTS data_quality_alerts
        ADD COLUMN IF NOT EXISTS resolution_notes TEXT
        """,
        """
        ALTER TABLE IF EXISTS data_quality_alerts
        ADD COLUMN IF NOT EXISTS resolved_by VARCHAR(255)
        """,
        """
        ALTER TABLE IF EXISTS data_quality_alerts
        ADD COLUMN IF NOT EXISTS resolved_at TIMESTAMP
        """,
        """
        ALTER TABLE IF EXISTS data_quality_alerts
        ADD COLUMN IF NOT EXISTS sla_due_at TIMESTAMP
        """,
        """
        ALTER TABLE IF EXISTS data_quality_alerts
        ADD COLUMN IF NOT EXISTS escalation_status VARCHAR(50)
        """,
    ]

    for statement in statements:
        connection.execute(text(statement))


def _alert_insert_params(alert: dict[str, Any]) -> dict[str, Any]:
    """Return only the fields stored in data_quality_alerts."""

    return {
        "run_id": alert.get("run_id"),
        "alert_type": alert.get("alert_type"),
        "severity": alert.get("severity"),
        "message": alert.get("message"),
        "owner_team": alert.get("owner_team", ""),
        "owner_email": alert.get("owner_email", ""),
        "assigned_to": alert.get("assigned_to", ""),
        "resolution_notes": alert.get("resolution_notes", ""),
    }


def _build_dataset_alerts(
    run_id: int,
    results: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Build dataset-level alerts from failed check results."""

    failed_results = [
        result for result in results
        if str(result.get("status", "")).upper() == "FAIL"
    ]

    grouped: dict[str, list[dict[str, Any]]] = {}
    for result in failed_results:
        dataset_name = result.get("dataset_name")
        if not dataset_name:
            continue
        grouped.setdefault(str(dataset_name), []).append(result)

    alerts = []

    for dataset_name, dataset_results in grouped.items():
        failed_count = len(dataset_results)
        highest_severity = _highest_severity(
            [result.get("severity") for result in dataset_results]
        )
        check_types = sorted({
            str(result.get("check_type"))
            for result in dataset_results
            if result.get("check_type")
        })
        primary_check_type = check_types[0] if len(check_types) == 1 else None

        alerts.append({
            "run_id": run_id,
            "alert_type": "DATASET_QUALITY_FAILURE",
            "severity": highest_severity,
            "dataset_name": dataset_name,
            "check_type": primary_check_type,
            "message": (
                f"Dataset {dataset_name} has {failed_count} failed check(s) "
                f"in run {run_id}. Check types: {', '.join(check_types) or 'N/A'}."
            ),
        })

    return alerts


def _with_owner(
    alert: dict[str, Any],
    ownership_rules: dict[str, Any],
) -> dict[str, Any]:
    """Attach owner metadata to an alert dictionary."""

    owner = determine_alert_owner(
        dataset_name=alert.get("dataset_name"),
        severity=alert.get("severity"),
        check_type=alert.get("check_type") or alert.get("alert_type"),
        rules=ownership_rules,
    )
    return {
        **alert,
        "owner_team": owner.get("owner_team", ""),
        "owner_email": owner.get("owner_email", ""),
        "slack_channel": owner.get("slack_channel", ""),
        "assigned_to": alert.get("assigned_to", ""),
        "resolution_notes": alert.get("resolution_notes", ""),
    }


def _deduplicate_alerts(alerts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Remove exact duplicate alert rows while preserving order."""

    seen = set()
    deduplicated = []

    for alert in alerts:
        key = (
            alert.get("run_id"),
            alert.get("alert_type"),
            alert.get("severity"),
            alert.get("dataset_name"),
            alert.get("message"),
        )
        if key in seen:
            continue
        seen.add(key)
        deduplicated.append(alert)

    return deduplicated


def _highest_severity(severities: list[Any]) -> str:
    """Return the highest known severity from a list."""

    severity_order = {
        "CRITICAL": 5,
        "HIGH": 4,
        "MEDIUM": 3,
        "LOW": 2,
        "INFO": 1,
        "NONE": 0,
    }
    normalized = [str(severity or "NONE").upper() for severity in severities]
    return max(normalized, key=lambda severity: severity_order.get(severity, 0))
