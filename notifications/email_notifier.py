import os
import smtplib
from email.message import EmailMessage
from pathlib import Path
from typing import Any

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")


def get_bool_env(key: str, default: bool = False) -> bool:
    value = os.getenv(key)

    if value is None:
        return default

    return value.strip().lower() in ["true", "1", "yes", "y"]


def get_alert_recipients() -> list[str]:
    recipients = os.getenv("ALERT_RECIPIENTS", "")

    return [
        email.strip()
        for email in recipients.split(",")
        if email.strip()
    ]


def build_alert_email_body(
    run_id: int,
    summary: dict[str, Any],
    alerts: list[dict[str, Any]]
) -> str:
    total_checks = summary.get("total_checks", 0)
    passed_checks = summary.get("passed_checks", 0)
    failed_checks = summary.get("failed_checks", 0)
    critical_checks = summary.get("critical_checks", 0)
    quality_score = summary.get("quality_score", 0)
    overall_status = summary.get("overall_status", "UNKNOWN")

    alert_lines = []

    for alert in alerts:
        alert_lines.append(
            f"""
Alert Type: {alert.get("alert_type")}
Severity: {alert.get("severity")}
Message: {alert.get("message")}
"""
        )

    alert_details = "\n".join(alert_lines)

    body = f"""
Automated Data Quality Monitoring Alert

Run ID: {run_id}
Overall Status: {overall_status}
Quality Score: {quality_score}%

Summary:
- Total Checks: {total_checks}
- Passed Checks: {passed_checks}
- Failed Checks: {failed_checks}
- Critical Checks: {critical_checks}

Alerts:
{alert_details}

Recommended Action:
Please open the Streamlit dashboard and review failed checks, critical issues, and bad-row examples.

Dashboard command:
python -m streamlit run dashboard/app.py

This message was generated automatically by the Automated Data Quality Monitoring System.
"""

    return body.strip()


def build_alert_email_html(
    run_id: int,
    summary: dict[str, Any],
    alerts: list[dict[str, Any]]
) -> str:
    total_checks = summary.get("total_checks", 0)
    passed_checks = summary.get("passed_checks", 0)
    failed_checks = summary.get("failed_checks", 0)
    critical_checks = summary.get("critical_checks", 0)
    quality_score = summary.get("quality_score", 0)
    overall_status = summary.get("overall_status", "UNKNOWN")

    alert_rows = ""

    for alert in alerts:
        alert_rows += f"""
        <tr>
            <td>{alert.get("alert_type")}</td>
            <td>{alert.get("severity")}</td>
            <td>{alert.get("message")}</td>
        </tr>
        """

    html = f"""
    <html>
        <body style="font-family: Arial, sans-serif; color: #222;">
            <h2>🚨 Automated Data Quality Alert</h2>

            <p>
                A data quality run has completed with issues that require attention.
            </p>

            <h3>Run Summary</h3>

            <table border="1" cellpadding="8" cellspacing="0" style="border-collapse: collapse;">
                <tr>
                    <th>Run ID</th>
                    <td>{run_id}</td>
                </tr>
                <tr>
                    <th>Overall Status</th>
                    <td>{overall_status}</td>
                </tr>
                <tr>
                    <th>Quality Score</th>
                    <td>{quality_score}%</td>
                </tr>
                <tr>
                    <th>Total Checks</th>
                    <td>{total_checks}</td>
                </tr>
                <tr>
                    <th>Passed Checks</th>
                    <td>{passed_checks}</td>
                </tr>
                <tr>
                    <th>Failed Checks</th>
                    <td>{failed_checks}</td>
                </tr>
                <tr>
                    <th>Critical Checks</th>
                    <td>{critical_checks}</td>
                </tr>
            </table>

            <h3>Alerts</h3>

            <table border="1" cellpadding="8" cellspacing="0" style="border-collapse: collapse;">
                <tr>
                    <th>Alert Type</th>
                    <th>Severity</th>
                    <th>Message</th>
                </tr>
                {alert_rows}
            </table>

            <h3>Recommended Action</h3>
            <p>
                Open the Streamlit dashboard and review failed checks, critical issues,
                alerts, and bad-row examples.
            </p>

            <pre>python -m streamlit run dashboard/app.py</pre>

            <p style="font-size: 12px; color: #666;">
                This message was generated automatically by the Automated Data Quality Monitoring System.
            </p>
        </body>
    </html>
    """

    return html


def send_email(subject: str, plain_body: str, html_body: str | None = None) -> bool:
    enabled = get_bool_env("EMAIL_NOTIFICATIONS_ENABLED", False)

    if not enabled:
        print("📧 Email notifications are disabled.")
        return False

    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")
    from_name = os.getenv("EMAIL_FROM_NAME", "Data Quality Monitor")
    recipients = get_alert_recipients()

    if not smtp_host or not smtp_user or not smtp_password:
        print("⚠️ Email settings are incomplete. Check SMTP_HOST, SMTP_USER, and SMTP_PASSWORD.")
        return False

    if not recipients:
        print("⚠️ No alert recipients configured. Check ALERT_RECIPIENTS.")
        return False

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = f"{from_name} <{smtp_user}>"
    message["To"] = ", ".join(recipients)
    message.set_content(plain_body)

    if html_body:
        message.add_alternative(html_body, subtype="html")

    try:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(message)

        print(f"📧 Email notification sent to: {', '.join(recipients)}")
        return True

    except Exception as error:
        print(f"❌ Failed to send email notification: {error}")
        return False


def send_alert_email(
    run_id: int,
    summary: dict[str, Any],
    alerts: list[dict[str, Any]]
) -> bool:
    if not alerts:
        print("✅ No alerts found. Email notification skipped.")
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

    plain_body = build_alert_email_body(run_id, summary, alerts)
    html_body = build_alert_email_html(run_id, summary, alerts)

    return send_email(subject, plain_body, html_body)