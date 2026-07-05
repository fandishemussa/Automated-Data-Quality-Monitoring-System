"""Evaluate and persist dataset-level data quality SLA results."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

import yaml
from sqlalchemy import text
from sqlalchemy.engine import Engine

from utils.logger import get_logger


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SLA_RULES_PATH = PROJECT_ROOT / "config" / "sla_rules.yaml"

logger = get_logger(__name__)


CREATE_SLA_TABLE_SQL = """
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
"""

INSERT_SLA_RESULT_SQL = text(
    """
    INSERT INTO data_quality_sla_results (
        run_id,
        dataset_name,
        minimum_quality_score,
        actual_quality_score,
        max_critical_issues,
        actual_critical_issues,
        max_failed_checks,
        actual_failed_checks,
        sla_status,
        reason
    )
    VALUES (
        :run_id,
        :dataset_name,
        :minimum_quality_score,
        :actual_quality_score,
        :max_critical_issues,
        :actual_critical_issues,
        :max_failed_checks,
        :actual_failed_checks,
        :sla_status,
        :reason
    )
    """
)


def load_sla_rules(file_path: str | Path = DEFAULT_SLA_RULES_PATH) -> dict[str, Any]:
    """Load dataset SLA rules from YAML configuration."""

    path = Path(file_path)
    if not path.is_absolute():
        path = PROJECT_ROOT / path

    if not path.exists():
        raise FileNotFoundError(f"SLA rules file not found: {path}")

    with path.open("r", encoding="utf-8") as file:
        rules = yaml.safe_load(file) or {}

    if not isinstance(rules, dict):
        raise ValueError("SLA rules must be a YAML mapping of dataset names to thresholds.")

    return rules


def evaluate_sla_for_run(
    run_id: int,
    results: Iterable[dict[str, Any]],
    sla_rules: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Evaluate configured dataset SLAs for a completed monitoring run."""

    configured_rules = sla_rules if sla_rules is not None else load_sla_rules()
    if not configured_rules:
        logger.warning("No SLA rules configured. Skipping SLA evaluation for run %s.", run_id)
        return []

    result_rows = list(results or [])
    evaluated_results = []

    for dataset_name, dataset_rules in configured_rules.items():
        if not isinstance(dataset_rules, dict):
            logger.warning("Skipping invalid SLA rule for dataset %s.", dataset_name)
            continue

        dataset_results = [
            result for result in result_rows
            if result.get("dataset_name") == dataset_name
        ]
        metrics = _calculate_dataset_metrics(dataset_results)
        thresholds = _normalize_thresholds(dataset_rules)
        reasons = _build_sla_reasons(metrics, thresholds)

        evaluated_results.append({
            "run_id": int(run_id),
            "dataset_name": dataset_name,
            "minimum_quality_score": thresholds["minimum_quality_score"],
            "actual_quality_score": metrics["actual_quality_score"],
            "max_critical_issues": thresholds["max_critical_issues"],
            "actual_critical_issues": metrics["actual_critical_issues"],
            "max_failed_checks": thresholds["max_failed_checks"],
            "actual_failed_checks": metrics["actual_failed_checks"],
            "sla_status": "FAIL" if reasons else "PASS",
            "reason": "; ".join(reasons) if reasons else "SLA met.",
        })

    return evaluated_results


def ensure_sla_table_exists(engine: Engine) -> None:
    """Create the SLA results table when it is missing."""

    with engine.begin() as connection:
        connection.execute(text(CREATE_SLA_TABLE_SQL))


def save_sla_results(
    sla_results: Iterable[dict[str, Any]],
    engine: Engine | None = None,
) -> int:
    """Save SLA evaluation results to PostgreSQL and return the saved row count."""

    records = list(sla_results or [])
    if not records:
        logger.info("No SLA results to save.")
        return 0

    if engine is None:
        from data_sources.postgres_connector import create_monitor_engine

        engine = create_monitor_engine()

    ensure_sla_table_exists(engine)

    with engine.begin() as connection:
        for record in records:
            connection.execute(
                INSERT_SLA_RESULT_SQL,
                {
                    "run_id": int(record["run_id"]),
                    "dataset_name": record["dataset_name"],
                    "minimum_quality_score": float(record["minimum_quality_score"]),
                    "actual_quality_score": float(record["actual_quality_score"]),
                    "max_critical_issues": int(record["max_critical_issues"]),
                    "actual_critical_issues": int(record["actual_critical_issues"]),
                    "max_failed_checks": int(record["max_failed_checks"]),
                    "actual_failed_checks": int(record["actual_failed_checks"]),
                    "sla_status": record["sla_status"],
                    "reason": record["reason"],
                },
            )

    logger.info("Saved %s SLA result(s).", len(records))
    return len(records)


def _normalize_thresholds(dataset_rules: dict[str, Any]) -> dict[str, Any]:
    """Convert YAML SLA threshold values into predictable Python types."""

    return {
        "minimum_quality_score": _safe_float(
            dataset_rules.get("minimum_quality_score"),
            default=0.0,
        ),
        "max_critical_issues": _safe_int(
            dataset_rules.get("max_critical_issues"),
            default=0,
        ),
        "max_failed_checks": _safe_int(
            dataset_rules.get("max_failed_checks"),
            default=0,
        ),
        "freshness_hours": _safe_float(
            dataset_rules.get("freshness_hours"),
            default=None,
        ),
    }


def _calculate_dataset_metrics(dataset_results: list[dict[str, Any]]) -> dict[str, Any]:
    """Summarize scored check results for one dataset."""

    scored_results = [
        result for result in dataset_results
        if _normalize_status(result.get("status")) in {"PASS", "FAIL"}
    ]
    total_checks = len(scored_results)
    passed_checks = sum(
        1 for result in scored_results
        if _normalize_status(result.get("status")) == "PASS"
    )
    failed_results = [
        result for result in scored_results
        if _normalize_status(result.get("status")) == "FAIL"
    ]

    actual_quality_score = (
        round((passed_checks / total_checks) * 100, 2)
        if total_checks
        else 0.0
    )
    actual_critical_issues = sum(
        1 for result in failed_results
        if str(result.get("severity", "")).upper() == "CRITICAL"
    )
    freshness_failures = [
        result for result in failed_results
        if "freshness" in str(result.get("check_type", "")).lower()
    ]

    return {
        "total_checks": total_checks,
        "actual_quality_score": actual_quality_score,
        "actual_critical_issues": actual_critical_issues,
        "actual_failed_checks": len(failed_results),
        "freshness_failure_count": len(freshness_failures),
    }


def _build_sla_reasons(
    metrics: dict[str, Any],
    thresholds: dict[str, Any],
) -> list[str]:
    """Build human-readable SLA violation reasons."""

    reasons = []

    if metrics["total_checks"] == 0:
        reasons.append("No scored quality checks found for dataset.")

    if metrics["actual_quality_score"] < thresholds["minimum_quality_score"]:
        reasons.append(
            "Quality score "
            f"{metrics['actual_quality_score']} is below required "
            f"{thresholds['minimum_quality_score']}."
        )

    if metrics["actual_critical_issues"] > thresholds["max_critical_issues"]:
        reasons.append(
            "Critical issues "
            f"{metrics['actual_critical_issues']} exceed allowed "
            f"{thresholds['max_critical_issues']}."
        )

    if metrics["actual_failed_checks"] > thresholds["max_failed_checks"]:
        reasons.append(
            "Failed checks "
            f"{metrics['actual_failed_checks']} exceed allowed "
            f"{thresholds['max_failed_checks']}."
        )

    if thresholds["freshness_hours"] is not None and metrics["freshness_failure_count"] > 0:
        reasons.append(
            "Freshness check failed against configured target of "
            f"{thresholds['freshness_hours']} hour(s)."
        )

    return reasons


def _normalize_status(status: Any) -> str:
    """Normalize a result status value for comparisons."""

    return str(status or "").upper()


def _safe_float(value: Any, default: float | None) -> float | None:
    """Convert a value to float while preserving a supplied default."""

    if value is None:
        return default

    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int) -> int:
    """Convert a value to int while preserving a supplied default."""

    if value is None:
        return default

    try:
        return int(value)
    except (TypeError, ValueError):
        return default
