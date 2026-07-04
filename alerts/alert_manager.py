from sqlalchemy import text
from data_sources.postgres_connector import create_postgres_engine


def create_alerts_for_run(run_id, summary):
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
        print("No alerts created. Data quality looks good.")
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

    print(f" {len(alerts)} alert(s) created for run {run_id}.")
    return alerts