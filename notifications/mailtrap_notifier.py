import os
from pathlib import Path
from typing import Any

import mailtrap as mt
from dotenv import load_dotenv

from notifications.email_notifier import (
    build_alert_email_body,
    build_alert_email_html,
    get_alert_recipients,
    get_bool_env,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")


def send_mailtrap_email(
    subject: str,
    plain_body: str,
    html_body: str | None = None,
) -> bool:
    """
    Send an email using Mailtrap Email API.
    """

    enabled = get_bool_env("EMAIL_NOTIFICATIONS_ENABLED", False)

    if not enabled:
        print("📧 Email notifications are disabled.")
        return False

    api_token = os.getenv("MAILTRAP_API_TOKEN")
    sender_email = os.getenv("MAILTRAP_SENDER_EMAIL", "hello@demomailtrap.co")
    sender_name = os.getenv("MAILTRAP_SENDER_NAME", "Data Quality Monitor")
    recipients = get_alert_recipients()

    if not api_token:
        print("⚠️ MAILTRAP_API_TOKEN is missing in .env.")
        return False

    if not recipients:
        print("⚠️ No recipients configured. Check ALERT_RECIPIENTS in .env.")
        return False

    try:
        mail = mt.Mail(
            sender=mt.Address(
                email=sender_email,
                name=sender_name,
            ),
            to=[
                mt.Address(email=email)
                for email in recipients
            ],
            subject=subject,
            text=plain_body,
            html=html_body,
            category="Data Quality Alert",
        )

        client = mt.MailtrapClient(token=api_token)
        response = client.send(mail)

        print(f"📧 Mailtrap email notification sent to: {', '.join(recipients)}")
        print(f"Mailtrap response: {response}")

        return True

    except Exception as error:
        print(f"❌ Failed to send Mailtrap email notification: {error}")
        return False


def send_mailtrap_alert_email(
    run_id: int,
    summary: dict[str, Any],
    alerts: list[dict[str, Any]],
) -> bool:
    """
    Build and send a data quality alert email using Mailtrap.
    """

    if not alerts:
        print("✅ No alerts found. Mailtrap email skipped.")
        return False

    quality_score = summary.get("quality_score", 0)
    critical_checks = summary.get("critical_checks", 0)
    failed_checks = summary.get("failed_checks", 0)

    subject = (
        f"Data Quality Alert | Run {run_id} | "
        f"Score: {quality_score}% | "
        f"Failed: {failed_checks} | "
        f"Critical: {critical_checks}"
    )

    plain_body = build_alert_email_body(
        run_id=run_id,
        summary=summary,
        alerts=alerts,
    )

    html_body = build_alert_email_html(
        run_id=run_id,
        summary=summary,
        alerts=alerts,
    )

    return send_mailtrap_email(
        subject=subject,
        plain_body=plain_body,
        html_body=html_body,
    )