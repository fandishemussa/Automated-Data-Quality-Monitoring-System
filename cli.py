"""Command-line interface for common project operations."""

from __future__ import annotations

import argparse
import sys
from typing import Any

from sqlalchemy import text


def init_db_command(_args: argparse.Namespace) -> int:
    """Initialize monitoring database tables."""

    from database.init_db import initialize_database

    initialize_database()
    print("Database tables initialized successfully.")
    return 0


def run_checks_command(_args: argparse.Namespace) -> int:
    """Run the configured data quality checks."""

    from main import main as run_monitoring

    run_monitoring()
    return 0


def run_dashboard_command(_args: argparse.Namespace) -> int:
    """Print the Streamlit command used to launch the dashboard."""

    print("Run the dashboard with:")
    print("python -m streamlit run dashboard/app.py")
    return 0


def _format_latest_run(row: dict[str, Any]) -> str:
    """Format the latest run row for console output."""

    return "\n".join([
        f"Run ID: {row.get('run_id')}",
        f"Run Time: {row.get('run_time')}",
        f"Overall Status: {row.get('overall_status')}",
        f"Quality Score: {row.get('quality_score')}%",
        f"Total Checks: {row.get('total_checks')}",
        f"Passed Checks: {row.get('passed_checks')}",
        f"Failed Checks: {row.get('failed_checks')}",
        f"Critical Checks: {row.get('critical_checks')}",
    ])


def show_latest_run_command(_args: argparse.Namespace) -> int:
    """Print the latest data quality run summary."""

    from data_sources.postgres_connector import create_postgres_engine

    query = text(
        """
        SELECT *
        FROM data_quality_runs
        ORDER BY run_id DESC
        LIMIT 1
        """
    )

    engine = create_postgres_engine()

    with engine.begin() as connection:
        row = connection.execute(query).mappings().first()

    if row is None:
        print("No data quality runs found. Run `python cli.py run-checks` first.")
        return 1

    print(_format_latest_run(dict(row)))
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line argument parser."""

    parser = argparse.ArgumentParser(
        description="Automated Data Quality Monitoring System CLI",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_db_parser = subparsers.add_parser(
        "init-db",
        help="Create required PostgreSQL monitoring tables.",
    )
    init_db_parser.set_defaults(func=init_db_command)

    run_checks_parser = subparsers.add_parser(
        "run-checks",
        help="Run configured data quality checks.",
    )
    run_checks_parser.set_defaults(func=run_checks_command)

    run_dashboard_parser = subparsers.add_parser(
        "run-dashboard",
        help="Show the Streamlit command for launching the dashboard.",
    )
    run_dashboard_parser.set_defaults(func=run_dashboard_command)

    latest_run_parser = subparsers.add_parser(
        "show-latest-run",
        help="Print the latest data quality run summary.",
    )
    latest_run_parser.set_defaults(func=show_latest_run_command)

    return parser


def main() -> int:
    """Run the CLI and return a process exit code."""

    parser = build_parser()
    args = parser.parse_args()

    try:
        return args.func(args)
    except Exception as exc:
        print(f"Command failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
