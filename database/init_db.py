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

from data_sources.postgres_connector import create_monitor_engine
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
    """
    CREATE TABLE IF NOT EXISTS data_quality_sla_results (
        id SERIAL PRIMARY KEY,
        run_id INT,
        dataset_name VARCHAR(100),
        minimum_quality_score FLOAT,
        actual_quality_score FLOAT,
        max_critical_issues INT,
        actual_critical_issues INT,
        max_failed_checks INT,
        actual_failed_checks INT,
        sla_status VARCHAR(20),
        reason TEXT,
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
        std_dev FLOAT,
        value_distribution TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    ALTER TABLE IF EXISTS data_profile_results
    ADD COLUMN IF NOT EXISTS std_dev FLOAT
    """,
    """
    ALTER TABLE IF EXISTS data_profile_results
    ADD COLUMN IF NOT EXISTS value_distribution TEXT
    """,
    """
    CREATE TABLE IF NOT EXISTS data_lineage_edges (
        id SERIAL PRIMARY KEY,
        source_table VARCHAR(100),
        source_column VARCHAR(100),
        target_table VARCHAR(100),
        target_column VARCHAR(100),
        relationship_type VARCHAR(100),
        description TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS audit_logs (
        id SERIAL PRIMARY KEY,
        event_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        event_type VARCHAR(100),
        module_name VARCHAR(100),
        actor VARCHAR(255),
        message TEXT,
        metadata TEXT
    )
    """,
]


def initialize_database():
    """Create all monitoring tables if they do not already exist."""

    logger.info("Initializing PostgreSQL monitoring database tables.")
    engine = create_monitor_engine()

    with engine.begin() as connection:
        for statement in CREATE_TABLE_STATEMENTS:
            connection.execute(text(statement))

    logger.info("Database initialization completed successfully.")


if __name__ == "__main__":
    initialize_database()
