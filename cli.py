"""Command-line interface for common project operations."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent
VERSION_FILE = PROJECT_ROOT / "VERSION"


def init_db_command(_args: argparse.Namespace) -> int:
    """Initialize monitoring database tables."""

    from database.init_db import initialize_database

    initialize_database()
    print("Database tables initialized successfully.")
    return 0


def seed_demo_command(args: argparse.Namespace) -> int:
    """Seed deterministic demo source tables."""

    from database.seed_sample_data import seed_sample_data

    seed_sample_data(reset=not args.no_reset)
    print("Demo source tables seeded successfully.")
    return 0


def run_checks_command(_args: argparse.Namespace) -> int:
    """Run the configured data quality checks."""

    from main import main as run_monitoring

    run_monitoring()
    return 0


def escalate_alerts_command(_args: argparse.Namespace) -> int:
    """Escalate unresolved alerts that are past their SLA window."""

    from alerts.escalation import run_alert_escalation

    escalated_alerts = run_alert_escalation()
    print(f"Escalated {len(escalated_alerts)} alert(s).")
    return 0


def validate_config_command(_args: argparse.Namespace) -> int:
    """Validate environment, database, and rules configuration."""

    from utils.config_validator import has_failures, print_validation_report, validate_config

    results = validate_config()
    print_validation_report(results)
    return 1 if has_failures(results) else 0


def dashboard_command(args: argparse.Namespace) -> int:
    """Print or run the Streamlit dashboard command."""

    command = [sys.executable, "-m", "streamlit", "run", "dashboard/app.py"]
    print("Dashboard command:")
    print("python -m streamlit run dashboard/app.py")

    if args.run:
        return subprocess.run(command, cwd=PROJECT_ROOT, check=False).returncode

    return 0


def api_command(args: argparse.Namespace) -> int:
    """Print or run the FastAPI development server command."""

    command = [sys.executable, "-m", "uvicorn", "api.app:app", "--reload"]
    print("API command:")
    print("uvicorn api.app:app --reload")

    if args.run:
        return subprocess.run(command, cwd=PROJECT_ROOT, check=False).returncode

    return 0


def version_command(_args: argparse.Namespace) -> int:
    """Print the project version."""

    print(read_version())
    return 0


def demo_command(_args: argparse.Namespace) -> int:
    """Initialize, seed, run checks, and print the dashboard command."""

    for command in [init_db_command, seed_demo_command, run_checks_command]:
        args = argparse.Namespace(no_reset=False)
        exit_code = command(args)
        if exit_code != 0:
            return exit_code

    print("")
    print("Demo run complete. Launch the dashboard with:")
    print("python -m streamlit run dashboard/app.py")
    return 0


def build_release_command(_args: argparse.Namespace) -> int:
    """Build a downloadable release archive."""

    from scripts.build_release import main as build_release

    return build_release()


def release_audit_command(_args: argparse.Namespace) -> int:
    """Run release-readiness checks."""

    from scripts.release_audit import main as release_audit

    return release_audit()


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

    from sqlalchemy import text

    from data_sources.postgres_connector import create_monitor_engine

    query = text(
        """
        SELECT *
        FROM data_quality_runs
        ORDER BY run_id DESC
        LIMIT 1
        """
    )

    engine = create_monitor_engine()

    with engine.begin() as connection:
        row = connection.execute(query).mappings().first()

    if row is None:
        print("No data quality runs found. Run `python cli.py run-checks` first.")
        return 1

    print(_format_latest_run(dict(row)))
    return 0


def read_version() -> str:
    """Read the project version from VERSION."""

    if VERSION_FILE.exists():
        return VERSION_FILE.read_text(encoding="utf-8").strip()
    return "0.0.0"


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line argument parser."""

    parser = argparse.ArgumentParser(
        description="Automated Data Quality Monitoring System CLI",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser(
        "validate-config",
        help="Validate environment, rules, source DB, and monitoring DB setup.",
    )
    validate_parser.set_defaults(func=validate_config_command)

    init_db_parser = subparsers.add_parser(
        "init-db",
        help="Create required PostgreSQL monitoring tables.",
    )
    init_db_parser.set_defaults(func=init_db_command)

    seed_demo_parser = subparsers.add_parser(
        "seed-demo",
        help="Create and seed demo source tables.",
    )
    seed_demo_parser.add_argument(
        "--no-reset",
        action="store_true",
        help="Create tables and reload rows without dropping the sample tables.",
    )
    seed_demo_parser.set_defaults(func=seed_demo_command)

    run_checks_parser = subparsers.add_parser(
        "run-checks",
        help="Run configured data quality checks.",
    )
    run_checks_parser.set_defaults(func=run_checks_command)

    escalate_alerts_parser = subparsers.add_parser(
        "escalate-alerts",
        help="Escalate unresolved CRITICAL/HIGH alerts that are past SLA.",
    )
    escalate_alerts_parser.set_defaults(func=escalate_alerts_command)

    dashboard_parser = subparsers.add_parser(
        "dashboard",
        help="Show the Streamlit command, or run it with --run.",
    )
    dashboard_parser.add_argument(
        "--run",
        action="store_true",
        help="Launch Streamlit from the CLI.",
    )
    dashboard_parser.set_defaults(func=dashboard_command)

    run_dashboard_parser = subparsers.add_parser(
        "run-dashboard",
        help="Backward-compatible alias for `dashboard`.",
    )
    run_dashboard_parser.add_argument("--run", action="store_true")
    run_dashboard_parser.set_defaults(func=dashboard_command)

    api_parser = subparsers.add_parser(
        "api",
        help="Show the API command, or run it with --run.",
    )
    api_parser.add_argument(
        "--run",
        action="store_true",
        help="Launch Uvicorn from the CLI.",
    )
    api_parser.set_defaults(func=api_command)

    version_parser = subparsers.add_parser(
        "version",
        help="Print the project version.",
    )
    version_parser.set_defaults(func=version_command)

    demo_parser = subparsers.add_parser(
        "demo",
        help="Initialize the database, seed demo data, run checks, and show dashboard command.",
    )
    demo_parser.set_defaults(func=demo_command)

    build_release_parser = subparsers.add_parser(
        "build-release",
        help="Create a release ZIP archive.",
    )
    build_release_parser.set_defaults(func=build_release_command)

    release_audit_parser = subparsers.add_parser(
        "release-audit",
        help="Run release-readiness checks.",
    )
    release_audit_parser.set_defaults(func=release_audit_command)

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
