"""Row volume anomaly detection for monitored datasets."""

from __future__ import annotations

import json
from typing import Any

import pandas as pd
from sqlalchemy import text

from checks.rule_engine import build_result, make_message_detail
from data_sources.postgres_connector import create_monitor_engine
from utils.logger import get_logger


logger = get_logger(__name__)

CHECK_TYPE = "row_volume_anomaly_check"
DEFAULT_BASELINE_RUNS = 5
DEFAULT_CHANGE_THRESHOLD_PERCENT = 40
DEFAULT_VOLUME_SEVERITY = "HIGH"

CREATE_VOLUME_HISTORY_TABLE_SQL = text(
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
    """
)

INSERT_VOLUME_HISTORY_SQL = text(
    """
    INSERT INTO data_volume_history (
        run_id,
        dataset_name,
        row_count,
        baseline_row_count,
        percent_change,
        status,
        severity
    )
    VALUES (
        :run_id,
        :dataset_name,
        :row_count,
        :baseline_row_count,
        :percent_change,
        :status,
        :severity
    )
    """
)


def get_historical_row_counts(dataset_name: str, baseline_runs: int) -> list[int]:
    """Return recent historical row counts for a dataset."""

    ensure_volume_history_table_exists()
    query = text(
        """
        SELECT row_count
        FROM data_volume_history
        WHERE dataset_name = :dataset_name
          AND row_count IS NOT NULL
        ORDER BY run_id DESC, id DESC
        LIMIT :baseline_runs
        """
    )

    try:
        engine = create_monitor_engine()
        with engine.begin() as connection:
            rows = connection.execute(
                query,
                {
                    "dataset_name": dataset_name,
                    "baseline_runs": max(int(baseline_runs), 1),
                },
            ).mappings().all()
    except Exception:
        logger.exception("Could not load row volume history for %s.", dataset_name)
        return []

    return [int(row["row_count"]) for row in rows if row.get("row_count") is not None]


def calculate_row_count_change(current_count: int, baseline_count: float) -> float:
    """Return signed percentage change from baseline to current row count."""

    baseline = float(baseline_count or 0)
    current = float(current_count or 0)

    if baseline == 0:
        return 0.0 if current == 0 else 100.0

    return round(((current - baseline) / baseline) * 100, 2)


def save_volume_history(
    run_id: int,
    dataset_name: str,
    row_count: int,
    baseline_row_count: float,
    percent_change: float,
    status: str,
    severity: str,
) -> int:
    """Persist one row volume history record."""

    ensure_volume_history_table_exists()
    engine = create_monitor_engine()
    with engine.begin() as connection:
        result = connection.execute(
            INSERT_VOLUME_HISTORY_SQL,
            {
                "run_id": int(run_id),
                "dataset_name": dataset_name,
                "row_count": int(row_count),
                "baseline_row_count": float(baseline_row_count),
                "percent_change": float(percent_change),
                "status": status,
                "severity": severity,
            },
        )

    logger.info(
        "Saved row volume history for dataset=%s run_id=%s status=%s.",
        dataset_name,
        run_id,
        status,
    )
    return int(result.rowcount or 0)


def run_volume_anomaly_check(
    run_id: int,
    dataset_name: str,
    current_df: pd.DataFrame,
    volume_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run row volume anomaly detection for one loaded dataset."""

    config = volume_config or {}
    if not _enabled(config):
        return build_result(
            dataset_name=dataset_name,
            check_type=CHECK_TYPE,
            column_name=None,
            rule="volume_anomaly_detection_disabled",
            total_rows=0,
            failed_rows=0,
            status="SKIPPED",
            details=make_message_detail(
                dataset_name,
                CHECK_TYPE,
                None,
                "Row volume anomaly detection is disabled.",
            ),
        )

    baseline_runs = _safe_int(config.get("baseline_runs"), DEFAULT_BASELINE_RUNS)
    threshold = _safe_float(
        config.get("change_threshold_percent"),
        DEFAULT_CHANGE_THRESHOLD_PERCENT,
    )
    configured_severity = str(config.get("severity", DEFAULT_VOLUME_SEVERITY)).upper()
    current_count = int(len(current_df))

    history = get_historical_row_counts(dataset_name, baseline_runs)

    if not history:
        return _save_and_return_baseline_result(
            run_id=run_id,
            dataset_name=dataset_name,
            current_count=current_count,
        )

    baseline_count = round(sum(history) / len(history), 2)
    percent_change = calculate_row_count_change(current_count, baseline_count)
    is_anomaly = abs(percent_change) > threshold
    status = "FAIL" if is_anomaly else "PASS"
    severity = configured_severity if is_anomaly else "NONE"

    details = []
    if is_anomaly:
        details = [_volume_issue_detail(
            dataset_name=dataset_name,
            current_count=current_count,
            baseline_count=baseline_count,
            percent_change=percent_change,
            threshold=threshold,
            baseline_runs=len(history),
        )]

    save_error = None
    try:
        save_volume_history(
            run_id=run_id,
            dataset_name=dataset_name,
            row_count=current_count,
            baseline_row_count=baseline_count,
            percent_change=percent_change,
            status=status,
            severity=severity,
        )
    except Exception as exc:
        save_error = exc
        logger.exception("Could not save row volume history for %s.", dataset_name)

    if save_error:
        status = "FAIL"
        severity = configured_severity
        details.extend(
            make_message_detail(
                dataset_name,
                CHECK_TYPE,
                None,
                f"Could not save row volume history: {save_error}",
            )
        )

    result = build_result(
        dataset_name=dataset_name,
        check_type=CHECK_TYPE,
        column_name=None,
        rule=(
            f"baseline_runs={baseline_runs}; "
            f"change_threshold_percent={threshold:g}"
        ),
        total_rows=current_count,
        failed_rows=1 if status == "FAIL" else 0,
        status=status,
        details=details,
    )
    result["severity"] = severity
    return result


def ensure_volume_history_table_exists() -> None:
    """Create row volume history table if it is missing."""

    engine = create_monitor_engine()
    with engine.begin() as connection:
        connection.execute(CREATE_VOLUME_HISTORY_TABLE_SQL)


def _save_and_return_baseline_result(
    run_id: int,
    dataset_name: str,
    current_count: int,
) -> dict[str, Any]:
    """Save the first observed row count and return a skipped baseline result."""

    try:
        save_volume_history(
            run_id=run_id,
            dataset_name=dataset_name,
            row_count=current_count,
            baseline_row_count=float(current_count),
            percent_change=0.0,
            status="SKIPPED",
            severity="LOW",
        )
    except Exception as exc:
        logger.exception("Could not save baseline row volume for %s.", dataset_name)
        result = build_result(
            dataset_name=dataset_name,
            check_type=CHECK_TYPE,
            column_name=None,
            rule="baseline_row_volume",
            total_rows=current_count,
            failed_rows=1,
            status="FAIL",
            details=make_message_detail(
                dataset_name,
                CHECK_TYPE,
                None,
                f"Could not save baseline row volume history: {exc}",
            ),
        )
        result["severity"] = DEFAULT_VOLUME_SEVERITY
        return result

    result = build_result(
        dataset_name=dataset_name,
        check_type=CHECK_TYPE,
        column_name=None,
        rule="baseline_row_volume",
        total_rows=current_count,
        failed_rows=0,
        status="SKIPPED",
        details=make_message_detail(
            dataset_name,
            CHECK_TYPE,
            None,
            "No row volume history found. Saved current row count as baseline.",
        ),
    )
    result["severity"] = "LOW"
    return result


def _volume_issue_detail(
    dataset_name: str,
    current_count: int,
    baseline_count: float,
    percent_change: float,
    threshold: float,
    baseline_runs: int,
) -> dict[str, Any]:
    """Build an issue-detail row for a volume anomaly."""

    direction = "spike" if percent_change > 0 else "drop"
    payload = {
        "current_row_count": current_count,
        "baseline_row_count": baseline_count,
        "percent_change": percent_change,
        "threshold_percent": threshold,
        "baseline_runs": baseline_runs,
        "direction": direction,
    }
    return {
        "dataset_name": dataset_name,
        "check_type": CHECK_TYPE,
        "column_name": None,
        "row_identifier": "table_level",
        "bad_value": str(current_count),
        "reason": (
            f"Row count {direction} detected: current={current_count}, "
            f"baseline={baseline_count}, change={percent_change:.2f}%, "
            f"threshold={threshold:g}%."
        ),
        "sample_row": json.dumps(payload, sort_keys=True),
    }


def _enabled(config: dict[str, Any]) -> bool:
    """Return whether row volume anomaly detection is enabled."""

    return bool(config.get("enabled", False)) if isinstance(config, dict) else False


def _safe_int(value: Any, default: int) -> int:
    """Parse an integer config value with a fallback."""

    try:
        return max(int(value), 1)
    except (TypeError, ValueError):
        return int(default)


def _safe_float(value: Any, default: float) -> float:
    """Parse a float config value with a fallback."""

    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return float(default)

    return parsed if parsed >= 0 else float(default)
