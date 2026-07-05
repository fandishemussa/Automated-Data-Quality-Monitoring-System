"""Slack webhook notifications for data quality alerts."""

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


def send_slack_alert(
    run_id: int,
    summary: dict[str, Any],
    alerts: list[dict[str, Any]],
) -> bool:
    """Send data quality alerts to Slack using an incoming webhook."""

    if not alerts:
        logger.info("No alerts found. Slack notification skipped.")
        return False

    if not get_bool_env("SLACK_NOTIFICATIONS_ENABLED", False):
        logger.info("Slack notifications are disabled.")
        return False

    webhook_url = os.getenv("SLACK_WEBHOOK_URL", "").strip()
    if not webhook_url:
        logger.warning("SLACK_WEBHOOK_URL is missing. Slack notification skipped.")
        return False

    try:
        import requests
    except ImportError:
        logger.warning(
            "The requests package is required for Slack notifications. "
            "Install it with: pip install -r requirements.txt"
        )
        return False

    payload = {"text": build_slack_message(run_id, summary, alerts)}

    try:
        response = requests.post(webhook_url, json=payload, timeout=10)
    except requests.RequestException:
        logger.exception("Failed to send Slack alert for run %s.", run_id)
        return False

    if response.status_code != 200:
        logger.warning(
            "Slack notification failed for run %s with status %s: %s",
            run_id,
            response.status_code,
            response.text,
        )
        return False

    logger.info("Slack notification sent for run %s.", run_id)
    return True


def build_slack_message(
    run_id: int,
    summary: dict[str, Any],
    alerts: list[dict[str, Any]],
) -> str:
    """Build a Slack-friendly plain text message."""

    alert_lines = "\n".join(
        "- {severity} | {alert_type} | {owner} ({owner_email}): {message}".format(
            severity=alert.get("severity", "UNKNOWN"),
            alert_type=alert.get("alert_type", "UNKNOWN"),
            owner=alert.get("owner_team") or "Unassigned",
            owner_email=alert.get("owner_email") or "N/A",
            message=alert.get("message", ""),
        )
        for alert in alerts
    )

    return f"""
*Data Quality Alert*
Run ID: {run_id}
Overall status: {summary.get("overall_status", "UNKNOWN")}
Quality score: {summary.get("quality_score", 0)}%
Total checks: {summary.get("total_checks", 0)}
Failed checks: {summary.get("failed_checks", 0)}
Critical checks: {summary.get("critical_checks", 0)}

*Alerts*
{alert_lines}

Recommended dashboard command:
`python -m streamlit run dashboard/app.py`
""".strip()
