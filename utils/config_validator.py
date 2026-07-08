"""Configuration validation helpers for local runs and release checks."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv
from sqlalchemy import text

from config.settings import ENV_FILE, PROJECT_ROOT, get_bool_env


ValidationResult = dict[str, str]

REQUIRED_DB_SUFFIXES = ["USER", "PASSWORD", "HOST", "PORT", "NAME"]
REQUIRED_MONITORING_TABLES = [
    "data_quality_runs",
    "data_quality_results",
    "data_quality_issue_details",
    "data_quality_alerts",
    "data_profile_results",
    "data_quality_sla_results",
    "data_lineage_edges",
    "data_schema_snapshots",
    "data_volume_history",
    "audit_logs",
]
IGNORED_RULE_SECTIONS = {
    "global_rules",
    "cross_table_validations",
    "quality_thresholds",
}


def validate_config(check_connections: bool = True) -> list[ValidationResult]:
    """Validate environment, rules, source DB, and monitoring DB configuration."""

    load_dotenv(ENV_FILE)
    results: list[ValidationResult] = []

    results.append(_validate_environment_available())
    rules, rules_results = _validate_rules_file()
    results.extend(rules_results)

    source_tables: list[str] | None = None

    if check_connections:
        source_result, source_tables = _validate_source_connection()
        results.append(source_result)

        monitor_result = _validate_monitor_connection()
        results.append(monitor_result)
        results.append(_validate_monitoring_tables())
    else:
        results.append(_warning(
            "database connection checks",
            "Connection checks were skipped.",
            "Run `python cli.py validate-config` before a real monitoring run.",
        ))

    results.append(_validate_source_tables_in_rules(rules, source_tables))
    results.append(_validate_dashboard_auth())
    results.append(_validate_optional_service(
        service_name="Mailtrap email notifications",
        enabled_var="EMAIL_NOTIFICATIONS_ENABLED",
        required_vars=["MAILTRAP_API_TOKEN", "ALERT_RECIPIENTS"],
        recommended_fix=(
            "Set EMAIL_NOTIFICATIONS_ENABLED=false, or configure "
            "MAILTRAP_API_TOKEN and ALERT_RECIPIENTS."
        ),
    ))
    results.append(_validate_optional_service(
        service_name="Slack notifications",
        enabled_var="SLACK_NOTIFICATIONS_ENABLED",
        required_vars=["SLACK_WEBHOOK_URL"],
        recommended_fix=(
            "Set SLACK_NOTIFICATIONS_ENABLED=false, or configure SLACK_WEBHOOK_URL."
        ),
    ))
    results.append(_validate_optional_service(
        service_name="Teams notifications",
        enabled_var="TEAMS_NOTIFICATIONS_ENABLED",
        required_vars=["TEAMS_WEBHOOK_URL"],
        recommended_fix=(
            "Set TEAMS_NOTIFICATIONS_ENABLED=false, or configure TEAMS_WEBHOOK_URL."
        ),
    ))

    return results


def print_validation_report(results: list[ValidationResult] | None = None) -> None:
    """Print a PowerShell-friendly validation report."""

    validation_results = results if results is not None else validate_config()
    print("Configuration validation report")
    print("--------------------------------")

    for result in validation_results:
        print(f"[{result['status']}] {result['name']}: {result['message']}")
        if result["status"] != "PASS" and result.get("recommended_fix"):
            print(f"  Fix: {result['recommended_fix']}")


def has_failures(
    results: list[ValidationResult],
    required_names: set[str] | None = None,
) -> bool:
    """Return True when validation has FAIL results, optionally by result name."""

    for result in results:
        if result["status"] != "FAIL":
            continue
        if required_names is None or result["name"] in required_names:
            return True
    return False


def _validate_environment_available() -> ValidationResult:
    """Check whether a .env file or enough process env vars are available."""

    if ENV_FILE.exists():
        return _pass(
            "environment",
            f"Environment file found at {ENV_FILE.name}.",
            "",
        )

    legacy_complete = _env_group_complete("DB")
    source_complete = _env_group_complete("SOURCE_DB") or legacy_complete
    monitor_complete = _env_group_complete("MONITOR_DB") or legacy_complete

    if source_complete and monitor_complete:
        return _pass(
            "environment",
            "Required database environment variables are available in the shell.",
            "",
        )

    return _fail(
        "environment",
        "No .env file found and required database variables are incomplete.",
        "Copy `.env.example` to `.env`, then fill in DB_* or SOURCE_DB_*/MONITOR_DB_* values.",
    )


def _validate_rules_file() -> tuple[dict[str, Any], list[ValidationResult]]:
    """Validate rules.yaml existence and parseability."""

    rules_path = PROJECT_ROOT / "config" / "rules.yaml"
    results: list[ValidationResult] = []

    if not rules_path.exists():
        return {}, [
            _fail(
                "rules.yaml exists",
                "config/rules.yaml was not found.",
                "Copy `config/rules.example.yaml` to `config/rules.yaml` and edit it.",
            )
        ]

    results.append(_pass(
        "rules.yaml exists",
        "config/rules.yaml exists.",
        "",
    ))

    try:
        with rules_path.open("r", encoding="utf-8") as rules_file:
            rules = yaml.safe_load(rules_file) or {}
    except yaml.YAMLError as exc:
        return {}, results + [
            _fail(
                "rules.yaml valid",
                f"config/rules.yaml is not valid YAML: {_safe_error_message(exc)}",
                "Fix the YAML syntax, then run `python cli.py validate-config` again.",
            )
        ]

    if not isinstance(rules, dict):
        return {}, results + [
            _fail(
                "rules.yaml valid",
                "config/rules.yaml must be a YAML mapping.",
                "Use dataset names as top-level keys.",
            )
        ]

    results.append(_pass(
        "rules.yaml valid",
        "config/rules.yaml parsed successfully.",
        "",
    ))
    return rules, results


def _validate_source_connection() -> tuple[ValidationResult, list[str] | None]:
    """Validate source database/table-list access."""

    try:
        from data_sources.source_factory import get_source_functions, get_source_type

        source_type = get_source_type()
        source = get_source_functions(source_type)
        table_names = source.get_table_names()
    except Exception as exc:
        return (
            _fail(
                "source database connection",
                f"Could not connect to the configured source database: {_safe_error_message(exc)}",
                "Check SOURCE_DB_TYPE and source database environment variables.",
            ),
            None,
        )

    return (
        _pass(
            "source database connection",
            f"Connected to source database and found {len(table_names)} table(s).",
            "",
        ),
        table_names,
    )


def _validate_monitor_connection() -> ValidationResult:
    """Validate monitoring database connectivity."""

    try:
        from data_sources.postgres_connector import create_monitor_engine

        engine = create_monitor_engine()
        with engine.begin() as connection:
            connection.execute(text("SELECT 1"))
    except Exception as exc:
        return _fail(
            "monitoring database connection",
            f"Could not connect to the monitoring database: {_safe_error_message(exc)}",
            "Check MONITOR_DB_* or DB_* variables, then run `python cli.py validate-config`.",
        )

    return _pass(
        "monitoring database connection",
        "Monitoring database connection succeeded.",
        "",
    )


def _validate_monitoring_tables() -> ValidationResult:
    """Validate required monitoring tables exist."""

    try:
        from data_sources.postgres_connector import create_monitor_engine

        engine = create_monitor_engine()
        with engine.begin() as connection:
            existing_tables = set(connection.execute(text(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                """
            )).scalars().all())
    except Exception as exc:
        return _fail(
            "monitoring tables",
            f"Could not inspect monitoring tables: {_safe_error_message(exc)}",
            "Run `python cli.py init-db` after fixing monitoring database connectivity.",
        )

    missing_tables = [
        table_name
        for table_name in REQUIRED_MONITORING_TABLES
        if table_name not in existing_tables
    ]

    if missing_tables:
        return _fail(
            "monitoring tables",
            "Missing monitoring table(s): " + ", ".join(missing_tables),
            "Run `python cli.py init-db`.",
        )

    return _pass(
        "monitoring tables",
        "All required monitoring tables exist.",
        "",
    )


def _validate_source_tables_in_rules(
    rules: dict[str, Any],
    source_tables: list[str] | None,
) -> ValidationResult:
    """Validate datasets referenced by rules.yaml exist in the source DB."""

    dataset_names = _dataset_names_from_rules(rules)

    if not dataset_names:
        return _warning(
            "source tables referenced in rules",
            "No dataset rule sections were found in config/rules.yaml.",
            "Add dataset sections such as customers, orders, or products.",
        )

    if source_tables is None:
        return _warning(
            "source tables referenced in rules",
            "Skipped source-table validation because the source connection failed.",
            "Fix the source database connection, then rerun validation.",
        )

    missing_tables = sorted(set(dataset_names) - set(source_tables))

    if missing_tables:
        return _fail(
            "source tables referenced in rules",
            "Rules reference missing source table(s): " + ", ".join(missing_tables),
            "Seed demo data with `python cli.py seed-demo` or update config/rules.yaml.",
        )

    return _pass(
        "source tables referenced in rules",
        "Every dataset in config/rules.yaml exists in the source database.",
        "",
    )


def _validate_dashboard_auth() -> ValidationResult:
    """Validate dashboard authentication settings when enabled."""

    if not get_bool_env("DASHBOARD_AUTH_ENABLED", False):
        return _pass(
            "dashboard authentication",
            "Dashboard authentication is disabled.",
            "",
        )

    username = os.getenv("DASHBOARD_USERNAME", "").strip()
    password = os.getenv("DASHBOARD_PASSWORD", "").strip()
    password_hash = os.getenv("DASHBOARD_PASSWORD_HASH", "").strip()

    if username and (password or password_hash):
        return _pass(
            "dashboard authentication",
            "Dashboard authentication is enabled and credentials are configured.",
            "",
        )

    return _fail(
        "dashboard authentication",
        "Dashboard authentication is enabled, but credentials are incomplete.",
        "Set DASHBOARD_USERNAME and either DASHBOARD_PASSWORD or DASHBOARD_PASSWORD_HASH.",
    )


def _validate_optional_service(
    service_name: str,
    enabled_var: str,
    required_vars: list[str],
    recommended_fix: str,
) -> ValidationResult:
    """Validate optional notification settings without exposing secrets."""

    if not get_bool_env(enabled_var, False):
        return _pass(
            service_name,
            f"{service_name} are disabled.",
            "",
        )

    missing = [
        variable
        for variable in required_vars
        if not os.getenv(variable, "").strip()
    ]

    if missing:
        return _fail(
            service_name,
            "Missing required variable(s): " + ", ".join(missing),
            recommended_fix,
        )

    return _pass(
        service_name,
        f"{service_name} are enabled and configured.",
        "",
    )


def _dataset_names_from_rules(rules: dict[str, Any]) -> list[str]:
    """Return top-level dataset names from rules.yaml."""

    return [
        name
        for name, value in rules.items()
        if name not in IGNORED_RULE_SECTIONS and isinstance(value, dict)
    ]


def _env_group_complete(prefix: str) -> bool:
    """Return whether all required database vars for a prefix are set."""

    return all(os.getenv(f"{prefix}_{suffix}", "").strip() for suffix in REQUIRED_DB_SUFFIXES)


def _safe_error_message(exc: Exception) -> str:
    """Return a short error message with common secret patterns redacted."""

    message = str(exc).splitlines()[0] if str(exc) else exc.__class__.__name__
    message = re.sub(r"://([^:\s/@]+):([^@\s]+)@", r"://***:***@", message)
    message = re.sub(
        r"(?i)(password|token|secret|webhook_url)=([^,\s)]+)",
        r"\1=***",
        message,
    )
    return f"{exc.__class__.__name__}: {message[:300]}"


def _pass(name: str, message: str, recommended_fix: str) -> ValidationResult:
    """Build a PASS validation result."""

    return _result(name, "PASS", message, recommended_fix)


def _warning(name: str, message: str, recommended_fix: str) -> ValidationResult:
    """Build a WARNING validation result."""

    return _result(name, "WARNING", message, recommended_fix)


def _fail(name: str, message: str, recommended_fix: str) -> ValidationResult:
    """Build a FAIL validation result."""

    return _result(name, "FAIL", message, recommended_fix)


def _result(
    name: str,
    status: str,
    message: str,
    recommended_fix: str,
) -> ValidationResult:
    """Build one structured validation result."""

    return {
        "name": name,
        "status": status,
        "message": message,
        "recommended_fix": recommended_fix,
    }
