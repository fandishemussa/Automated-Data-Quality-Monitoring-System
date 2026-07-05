"""Microsoft Teams webhook notifications for data quality alerts."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from notifications.email_notifier import get_bool_env
from utils.logger import get_logger


PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")

logger = get_logger(__name__)


def send_teams_alert(
    run_id: int,
    summary: dict[str, Any],
    alerts: list[dict[str, Any]],
) -> bool:
    """Send data quality alerts to Microsoft Teams using an incoming webhook."""

    if not alerts:
        logger.info("No alerts found. Teams notification skipped.")
        return False

    if not get_bool_env("TEAMS_NOTIFICATIONS_ENABLED", False):
        logger.info("Teams notifications are disabled.")
        return False

    webhook_url = os.getenv("TEAMS_WEBHOOK_URL", "").strip()
    if not webhook_url:
        logger.warning("TEAMS_WEBHOOK_URL is missing. Teams notification skipped.")
        return False

    try:
        import requests
    except ImportError:
        logger.warning(
            "The requests package is required for Teams notifications. "
            "Install it with: pip install -r requirements.txt"
        )
        return False

    payload = build_teams_payload(run_id, summary, alerts)

    try:
        response = requests.post(webhook_url, json=payload, timeout=10)
    except requests.RequestException:
        logger.exception("Failed to send Teams alert for run %s.", run_id)
        return False

    if response.status_code not in {200, 202}:
        logger.warning(
            "Teams notification failed for run %s with status %s: %s",
            run_id,
            response.status_code,
            response.text,
        )
        return False

    logger.info("Teams notification sent for run %s.", run_id)
    return True


def build_teams_payload(
    run_id: int,
    summary: dict[str, Any],
    alerts: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build a Teams MessageCard payload."""

    alert_text = "\n\n".join(
        "- **{severity}** | {alert_type} | Owner: {owner} ({owner_email}) | {message}".format(
            severity=alert.get("severity", "UNKNOWN"),
            alert_type=alert.get("alert_type", "UNKNOWN"),
            owner=alert.get("owner_team") or "Unassigned",
            owner_email=alert.get("owner_email") or "N/A",
            message=alert.get("message", ""),
        )
        for alert in alerts
    )

    return {
        "@type": "MessageCard",
        "@context": "https://schema.org/extensions",
        "summary": "Data Quality Alert",
        "themeColor": "C62828",
        "title": "Data Quality Alert",
        "sections": [
            {
                "facts": [
                    {"name": "Run ID", "value": str(run_id)},
                    {"name": "Quality score", "value": f"{summary.get('quality_score', 0)}%"},
                    {"name": "Failed checks", "value": str(summary.get("failed_checks", 0))},
                    {"name": "Critical checks", "value": str(summary.get("critical_checks", 0))},
                ],
                "markdown": True,
            },
            {
                "activityTitle": "Alerts",
                "text": alert_text,
                "markdown": True,
            },
            {
                "activityTitle": "Dashboard review action",
                "text": "`python -m streamlit run dashboard/app.py`",
                "markdown": True,
            },
        ],
    }
