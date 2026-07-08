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
        escalated_at TIMESTAMP,
        escalation_level INT,
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
    ALTER TABLE IF EXISTS data_quality_alerts
    ADD COLUMN IF NOT EXISTS escalated_at TIMESTAMP
    """,
    """
    ALTER TABLE IF EXISTS data_quality_alerts
    ADD COLUMN IF NOT EXISTS escalation_level INT
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
    CREATE TABLE IF NOT EXISTS data_schema_snapshots (
        id SERIAL PRIMARY KEY,
        run_id INT,
        dataset_name VARCHAR(100),
        column_name VARCHAR(100),
        data_type VARCHAR(100),
        is_nullable VARCHAR(20),
        ordinal_position INT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS data_volume_history (
        id SERIAL PRIMARY KEY,
        run_id INT,
        dataset_name VARCHAR(100),
        row_count INT,
        baseline_row_count FLOAT,
        percent_change FLOAT,
        status VARCHAR(20),
        severity VARCHAR(20),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS audit_logs (
        id SERIAL PRIMARY KEY,
        event_type VARCHAR(100),
        username VARCHAR(255),
        role VARCHAR(100),
        entity_type VARCHAR(100),
        entity_id VARCHAR(100),
        old_value TEXT,
        new_value TEXT,
        ip_address VARCHAR(100),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS data_quality_users (
        id SERIAL PRIMARY KEY,
        username VARCHAR(100) UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        full_name VARCHAR(255),
        email VARCHAR(255),
        job_title VARCHAR(255),
        department VARCHAR(255),
        phone_number VARCHAR(100),
        role VARCHAR(50) DEFAULT 'viewer',
        is_active BOOLEAN DEFAULT TRUE,
        created_by VARCHAR(255),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_login_at TIMESTAMP
    )
    """,
    """
    ALTER TABLE IF EXISTS data_quality_users
    ADD COLUMN IF NOT EXISTS password_hash TEXT
    """,
    """
    ALTER TABLE IF EXISTS data_quality_users
    ADD COLUMN IF NOT EXISTS full_name VARCHAR(255)
    """,
    """
    ALTER TABLE IF EXISTS data_quality_users
    ADD COLUMN IF NOT EXISTS email VARCHAR(255)
    """,
    """
    ALTER TABLE IF EXISTS data_quality_users
    ADD COLUMN IF NOT EXISTS job_title VARCHAR(255)
    """,
    """
    ALTER TABLE IF EXISTS data_quality_users
    ADD COLUMN IF NOT EXISTS department VARCHAR(255)
    """,
    """
    ALTER TABLE IF EXISTS data_quality_users
    ADD COLUMN IF NOT EXISTS phone_number VARCHAR(100)
    """,
    """
    ALTER TABLE IF EXISTS data_quality_users
    ADD COLUMN IF NOT EXISTS role VARCHAR(50) DEFAULT 'viewer'
    """,
    """
    ALTER TABLE IF EXISTS data_quality_users
    ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE
    """,
    """
    ALTER TABLE IF EXISTS data_quality_users
    ADD COLUMN IF NOT EXISTS created_by VARCHAR(255)
    """,
    """
    ALTER TABLE IF EXISTS data_quality_users
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    """,
    """
    ALTER TABLE IF EXISTS data_quality_users
    ADD COLUMN IF NOT EXISTS last_login_at TIMESTAMP
    """,
    """
    CREATE TABLE IF NOT EXISTS data_quality_user_profile_updates (
        id SERIAL PRIMARY KEY,
        user_id INT,
        username VARCHAR(100),
        requested_changes TEXT,
        status VARCHAR(20) DEFAULT 'PENDING',
        submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        reviewed_by VARCHAR(255),
        reviewed_at TIMESTAMP,
        review_notes TEXT
    )
    """,
    """
    ALTER TABLE IF EXISTS data_quality_user_profile_updates
    ADD COLUMN IF NOT EXISTS requested_changes TEXT
    """,
    """
    ALTER TABLE IF EXISTS data_quality_user_profile_updates
    ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'PENDING'
    """,
    """
    ALTER TABLE IF EXISTS data_quality_user_profile_updates
    ADD COLUMN IF NOT EXISTS reviewed_by VARCHAR(255)
    """,
    """
    ALTER TABLE IF EXISTS data_quality_user_profile_updates
    ADD COLUMN IF NOT EXISTS reviewed_at TIMESTAMP
    """,
    """
    ALTER TABLE IF EXISTS data_quality_user_profile_updates
    ADD COLUMN IF NOT EXISTS review_notes TEXT
    """,
    """
    ALTER TABLE IF EXISTS audit_logs
    ADD COLUMN IF NOT EXISTS event_type VARCHAR(100)
    """,
    """
    ALTER TABLE IF EXISTS audit_logs
    ADD COLUMN IF NOT EXISTS username VARCHAR(255)
    """,
    """
    ALTER TABLE IF EXISTS audit_logs
    ADD COLUMN IF NOT EXISTS role VARCHAR(100)
    """,
    """
    ALTER TABLE IF EXISTS audit_logs
    ADD COLUMN IF NOT EXISTS entity_type VARCHAR(100)
    """,
    """
    ALTER TABLE IF EXISTS audit_logs
    ADD COLUMN IF NOT EXISTS entity_id VARCHAR(100)
    """,
    """
    ALTER TABLE IF EXISTS audit_logs
    ADD COLUMN IF NOT EXISTS old_value TEXT
    """,
    """
    ALTER TABLE IF EXISTS audit_logs
    ADD COLUMN IF NOT EXISTS new_value TEXT
    """,
    """
    ALTER TABLE IF EXISTS audit_logs
    ADD COLUMN IF NOT EXISTS ip_address VARCHAR(100)
    """,
    """
    ALTER TABLE IF EXISTS audit_logs
    ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    """,
    """
    CREATE TABLE IF NOT EXISTS data_cleaning_jobs (
        id SERIAL PRIMARY KEY,
        run_id INT,
        dataset_name VARCHAR(100),
        issue_id INT,
        cleaning_action VARCHAR(100),
        target_table VARCHAR(100),
        target_column VARCHAR(100),
        row_identifier VARCHAR(255),
        new_value TEXT,
        parameters TEXT,
        preview_rows TEXT,
        status VARCHAR(50),
        requested_by VARCHAR(255),
        approved_by VARCHAR(255),
        executed_by VARCHAR(255),
        total_rows_targeted INT,
        total_rows_updated INT,
        dry_run BOOLEAN DEFAULT TRUE,
        approval_required BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        approved_at TIMESTAMP NULL,
        executed_at TIMESTAMP NULL,
        error_message TEXT
    )
    """,
    """
    ALTER TABLE IF EXISTS data_cleaning_jobs
    ADD COLUMN IF NOT EXISTS row_identifier VARCHAR(255)
    """,
    """
    ALTER TABLE IF EXISTS data_cleaning_jobs
    ADD COLUMN IF NOT EXISTS new_value TEXT
    """,
    """
    ALTER TABLE IF EXISTS data_cleaning_jobs
    ADD COLUMN IF NOT EXISTS parameters TEXT
    """,
    """
    ALTER TABLE IF EXISTS data_cleaning_jobs
    ADD COLUMN IF NOT EXISTS preview_rows TEXT
    """,
    """
    ALTER TABLE IF EXISTS data_cleaning_jobs
    ADD COLUMN IF NOT EXISTS approval_required BOOLEAN DEFAULT TRUE
    """,
    """
    ALTER TABLE IF EXISTS data_cleaning_jobs
    ADD COLUMN IF NOT EXISTS approved_at TIMESTAMP NULL
    """,
    """
    ALTER TABLE IF EXISTS data_cleaning_jobs
    ADD COLUMN IF NOT EXISTS executed_at TIMESTAMP NULL
    """,
    """
    CREATE TABLE IF NOT EXISTS data_cleaning_change_log (
        id SERIAL PRIMARY KEY,
        job_id INT,
        dataset_name VARCHAR(100),
        table_name VARCHAR(100),
        column_name VARCHAR(100),
        row_identifier VARCHAR(255),
        old_value TEXT,
        new_value TEXT,
        change_reason TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS data_issue_status (
        id SERIAL PRIMARY KEY,
        issue_id INT,
        run_id INT,
        dataset_name VARCHAR(100),
        status VARCHAR(50),
        assigned_to VARCHAR(255),
        resolution_type VARCHAR(100),
        resolution_notes TEXT,
        updated_by VARCHAR(255),
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
