"""Airflow DAG for the Automated Data Quality Monitoring System.

The DAG intentionally runs the same project commands used locally. `main.py`
remains the single source of truth for data quality checks and notifications.
"""

from __future__ import annotations

import os
import shlex
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator


DAG_ID = "data_quality_monitoring"
PROJECT_ROOT = os.getenv("DQ_PROJECT_ROOT", "/opt/airflow/project")
PYTHON_BIN = os.getenv("DQ_PYTHON_BIN", "python")

COMMON_ENV = {
    "PYTHONPATH": PROJECT_ROOT,
    "DQ_PROJECT_ROOT": PROJECT_ROOT,
    "DB_USER": os.getenv("DB_USER", ""),
    "DB_PASSWORD": os.getenv("DB_PASSWORD", ""),
    "DB_HOST": os.getenv("DB_HOST", "postgres"),
    "DB_PORT": os.getenv("DB_PORT", "5432"),
    "DB_NAME": os.getenv("DB_NAME", "data_quality_db"),
    "DB_DRIVER": os.getenv("DB_DRIVER", "postgresql+psycopg2"),
    "EMAIL_NOTIFICATIONS_ENABLED": os.getenv("EMAIL_NOTIFICATIONS_ENABLED", "false"),
    "EMAIL_PROVIDER": os.getenv("EMAIL_PROVIDER", "mailtrap"),
    "ALERT_RECIPIENTS": os.getenv("ALERT_RECIPIENTS", ""),
    "MAILTRAP_API_TOKEN": os.getenv("MAILTRAP_API_TOKEN", ""),
    "MAILTRAP_SENDER_EMAIL": os.getenv("MAILTRAP_SENDER_EMAIL", ""),
    "MAILTRAP_SENDER_NAME": os.getenv("MAILTRAP_SENDER_NAME", "Data Quality Monitor"),
}


def project_command(command: str) -> str:
    """Build a shell command that runs from the mounted project root."""

    return f"cd {shlex.quote(PROJECT_ROOT)} && {command}"


default_args = {
    "owner": "data-quality",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}


with DAG(
    dag_id=DAG_ID,
    description="Run the automated data quality monitoring workflow daily.",
    default_args=default_args,
    start_date=datetime(2026, 1, 1),
    schedule="@daily",
    catchup=False,
    tags=["data-quality", "monitoring", "postgres"],
) as dag:
    initialize_database = BashOperator(
        task_id="initialize_database",
        bash_command=project_command(f"{PYTHON_BIN} database/init_db.py"),
        env=COMMON_ENV,
        append_env=True,
    )

    seed_sample_data = BashOperator(
        task_id="seed_sample_data",
        bash_command=project_command(
            "if [ \"${DQ_SEED_SAMPLE_DATA:-false}\" = \"true\" ]; then "
            f"{PYTHON_BIN} database/seed_sample_data.py; "
            "else echo 'Skipping sample data seed. Set DQ_SEED_SAMPLE_DATA=true to enable.'; "
            "fi"
        ),
        env={**COMMON_ENV, "DQ_SEED_SAMPLE_DATA": os.getenv("DQ_SEED_SAMPLE_DATA", "false")},
        append_env=True,
    )

    run_data_quality_checks = BashOperator(
        task_id="run_data_quality_checks",
        bash_command=project_command(f"{PYTHON_BIN} main.py"),
        env=COMMON_ENV,
        append_env=True,
    )

    send_notifications = BashOperator(
        task_id="send_notifications",
        bash_command=(
            "echo 'Notification handling is executed by main.py after "
            "quality checks and alert creation.'"
        ),
        env=COMMON_ENV,
        append_env=True,
    )

    initialize_database >> seed_sample_data >> run_data_quality_checks >> send_notifications
