from typing import Any

from sqlalchemy import text

from data_sources.postgres_connector import create_postgres_engine
from utils.logger import get_logger


logger = get_logger(__name__)


def create_alerts_for_run(
    run_id: int,
    summary: dict[str, Any],
) -> list[dict[str, Any]]:
    """Create alert records for a completed data quality run."""

    logger.info("Evaluating alerts for run %s.", run_id)

    alerts = []

    critical_checks = summary.get("critical_checks", 0)
    failed_checks = summary.get("failed_checks", 0)
    quality_score = summary.get("quality_score", 0)

    if critical_checks > 0:
        alerts.append({
            "run_id": run_id,
            "alert_type": "CRITICAL_DATA_QUALITY_ISSUE",
            "severity": "CRITICAL",
            "message": f"Run {run_id} has {critical_checks} critical data quality issue(s)."
        })

    if failed_checks > 0:
        alerts.append({
            "run_id": run_id,
            "alert_type": "DATA_QUALITY_FAILURE",
            "severity": "HIGH",
            "message": f"Run {run_id} has {failed_checks} failed data quality check(s)."
        })

    if quality_score < 75:
        alerts.append({
            "run_id": run_id,
            "alert_type": "LOW_QUALITY_SCORE",
            "severity": "MEDIUM",
            "message": f"Run {run_id} quality score is low: {quality_score}%."
        })

    if not alerts:
        logger.info("No alerts created for run %s. Data quality looks good.", run_id)
        return []

    engine = create_postgres_engine()

    insert_query = text("""
        INSERT INTO data_quality_alerts (
            run_id,
            alert_type,
            severity,
            message
        )
        VALUES (
            :run_id,
            :alert_type,
            :severity,
            :message
        )
    """)

    with engine.begin() as connection:
        for alert in alerts:
            connection.execute(insert_query, alert)
            logger.warning(
                "Created %s alert for run %s: %s",
                alert["severity"],
                run_id,
                alert["message"],
            )

    logger.info("%s alert(s) created for run %s.", len(alerts), run_id)
    return alerts
