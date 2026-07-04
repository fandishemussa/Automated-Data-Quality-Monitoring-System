"""Create the PostgreSQL tables required by the monitoring system.

Run from the project root:
    python database/init_db.py
"""

import sys
from pathlib import Path

from sqlalchemy import text


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from data_sources.postgres_connector import create_postgres_engine
from utils.logger import get_logger


logger = get_logger(__name__)


CREATE_TABLE_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS data_quality_runs (
        run_id SERIAL PRIMARY KEY,
        run_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        total_checks INT,
        passed_checks INT,
        failed_checks INT,
        critical_checks INT,
        quality_score FLOAT,
        overall_status VARCHAR(20)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS data_quality_results (
        id SERIAL PRIMARY KEY,
        run_id INT,
        dataset_name VARCHAR(100),
        check_type VARCHAR(100),
        column_name VARCHAR(100),
        rule TEXT,
        total_rows INT,
        failed_rows INT,
        failure_rate FLOAT,
        status VARCHAR(20),
        severity VARCHAR(20),
        run_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS data_quality_issue_details (
        id SERIAL PRIMARY KEY,
        run_id INT,
        result_id INT,
        dataset_name VARCHAR(100),
        check_type VARCHAR(100),
        column_name VARCHAR(100),
        row_identifier VARCHAR(255),
        bad_value TEXT,
        reason TEXT,
        sample_row TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS data_quality_alerts (
        id SERIAL PRIMARY KEY,
        run_id INT,
        alert_type VARCHAR(100),
        severity VARCHAR(20),
        message TEXT,
        is_resolved BOOLEAN DEFAULT FALSE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS data_profile_results (
        id SERIAL PRIMARY KEY,
        run_id INT,
        dataset_name VARCHAR(100),
        column_name VARCHAR(100),
        data_type VARCHAR(100),
        total_rows INT,
        null_count INT,
        null_rate FLOAT,
        unique_count INT,
        duplicate_count INT,
        min_value TEXT,
        max_value TEXT,
        mean FLOAT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
]


def initialize_database():
    """Create all monitoring tables if they do not already exist."""

    logger.info("Initializing PostgreSQL monitoring database tables.")
    engine = create_postgres_engine()

    with engine.begin() as connection:
        for statement in CREATE_TABLE_STATEMENTS:
            connection.execute(text(statement))

    logger.info("Database initialization completed successfully.")


if __name__ == "__main__":
    initialize_database()
