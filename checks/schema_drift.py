"""Schema drift detection for monitored source tables."""

from __future__ import annotations

import json
from typing import Any

import pandas as pd
from sqlalchemy import text

from checks.rule_engine import build_result, make_message_detail
from data_sources.postgres_connector import create_monitor_engine
from data_sources.source_factory import get_source_functions
from utils.logger import get_logger


logger = get_logger(__name__)

CHECK_TYPE = "schema_drift_check"
DEFAULT_SCHEMA_DRIFT_SEVERITY = "HIGH"

CREATE_SCHEMA_SNAPSHOT_TABLE_SQL = text(
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
    """
)

INSERT_SCHEMA_SNAPSHOT_SQL = text(
    """
    INSERT INTO data_schema_snapshots (
        run_id,
        dataset_name,
        column_name,
        data_type,
        is_nullable,
        ordinal_position
    )
    VALUES (
        :run_id,
        :dataset_name,
        :column_name,
        :data_type,
        :is_nullable,
        :ordinal_position
    )
    """
)


def get_current_schema(dataset_name: str) -> list[dict[str, Any]]:
    """Return normalized current schema metadata for a source dataset."""

    source = get_source_functions()
    description = source.get_table_description(dataset_name)

    if not isinstance(description, pd.DataFrame):
        description = pd.DataFrame(description)

    return normalize_schema(description)


def load_previous_schema_snapshot(dataset_name: str) -> list[dict[str, Any]]:
    """Load the latest saved schema snapshot for a dataset."""

    ensure_schema_snapshot_table_exists()
    query = text(
        """
        SELECT column_name, data_type, is_nullable, ordinal_position
        FROM data_schema_snapshots
        WHERE dataset_name = :dataset_name
          AND run_id = (
              SELECT MAX(run_id)
              FROM data_schema_snapshots
              WHERE dataset_name = :dataset_name
          )
        ORDER BY ordinal_position, id
        """
    )
    engine = create_monitor_engine()

    try:
        with engine.begin() as connection:
            rows = connection.execute(
                query,
                {"dataset_name": dataset_name},
            ).mappings().all()
    except Exception:
        logger.exception("Could not load schema snapshot for %s.", dataset_name)
        return []

    return normalize_schema(pd.DataFrame([dict(row) for row in rows]))


def compare_schema_snapshots(
    current_schema: list[dict[str, Any]],
    previous_schema: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Compare current and previous schemas and return drift changes."""

    current_by_name = {row["column_name"]: row for row in current_schema}
    previous_by_name = {row["column_name"]: row for row in previous_schema}
    changes: list[dict[str, Any]] = []

    for column_name, current_row in current_by_name.items():
        if column_name not in previous_by_name:
            changes.append(_change("added_column", column_name, None, current_row))

    for column_name, previous_row in previous_by_name.items():
        if column_name not in current_by_name:
            changes.append(_change("removed_column", column_name, previous_row, None))

    for column_name in sorted(set(current_by_name) & set(previous_by_name)):
        current_row = current_by_name[column_name]
        previous_row = previous_by_name[column_name]

        if current_row.get("data_type") != previous_row.get("data_type"):
            changes.append(
                _change(
                    "changed_data_type",
                    column_name,
                    previous_row,
                    current_row,
                    previous_value=previous_row.get("data_type"),
                    current_value=current_row.get("data_type"),
                )
            )

        if current_row.get("is_nullable") != previous_row.get("is_nullable"):
            changes.append(
                _change(
                    "changed_nullability",
                    column_name,
                    previous_row,
                    current_row,
                    previous_value=previous_row.get("is_nullable"),
                    current_value=current_row.get("is_nullable"),
                )
            )

        if current_row.get("ordinal_position") != previous_row.get("ordinal_position"):
            changes.append(
                _change(
                    "changed_column_order",
                    column_name,
                    previous_row,
                    current_row,
                    previous_value=previous_row.get("ordinal_position"),
                    current_value=current_row.get("ordinal_position"),
                )
            )

    return sorted(changes, key=lambda change: (str(change["column_name"]), str(change["change_type"])))


def save_schema_snapshot(
    run_id: int,
    dataset_name: str,
    current_schema: list[dict[str, Any]],
) -> int:
    """Persist a schema snapshot for a dataset and return inserted row count."""

    ensure_schema_snapshot_table_exists()
    rows = [
        {
            "run_id": int(run_id),
            "dataset_name": dataset_name,
            "column_name": row.get("column_name"),
            "data_type": row.get("data_type"),
            "is_nullable": row.get("is_nullable"),
            "ordinal_position": row.get("ordinal_position"),
        }
        for row in current_schema
    ]

    if not rows:
        return 0

    engine = create_monitor_engine()
    with engine.begin() as connection:
        connection.execute(INSERT_SCHEMA_SNAPSHOT_SQL, rows)

    logger.info("Saved %s schema snapshot row(s) for %s.", len(rows), dataset_name)
    return len(rows)


def run_schema_drift_check(
    run_id: int,
    dataset_name: str,
    drift_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run schema drift detection for one dataset and save the current snapshot."""

    config = drift_config or {}
    if not _enabled(config):
        return build_result(
            dataset_name=dataset_name,
            check_type=CHECK_TYPE,
            column_name=None,
            rule="schema_drift_detection_disabled",
            total_rows=0,
            failed_rows=0,
            status="SKIPPED",
            details=make_message_detail(
                dataset_name,
                CHECK_TYPE,
                None,
                "Schema drift detection is disabled.",
            ),
        )

    severity = str(config.get("severity", DEFAULT_SCHEMA_DRIFT_SEVERITY)).upper()

    try:
        current_schema = get_current_schema(dataset_name)
        previous_schema = load_previous_schema_snapshot(dataset_name)
    except Exception as exc:
        logger.exception("Schema drift check failed for %s.", dataset_name)
        return _result_with_severity(
            build_result(
                dataset_name=dataset_name,
                check_type=CHECK_TYPE,
                column_name=None,
                rule="schema_drift_detection",
                total_rows=0,
                failed_rows=1,
                status="FAIL",
                details=make_message_detail(
                    dataset_name,
                    CHECK_TYPE,
                    None,
                    f"Schema drift check failed: {exc}",
                ),
            ),
            severity,
        )

    if not previous_schema:
        try:
            save_schema_snapshot(run_id, dataset_name, current_schema)
        except Exception as exc:
            logger.exception("Could not save baseline schema snapshot for %s.", dataset_name)
            return _result_with_severity(
                build_result(
                    dataset_name=dataset_name,
                    check_type=CHECK_TYPE,
                    column_name=None,
                    rule="baseline_schema_snapshot",
                    total_rows=len(current_schema),
                    failed_rows=1,
                    status="FAIL",
                    details=make_message_detail(
                        dataset_name,
                        CHECK_TYPE,
                        None,
                        f"Could not save baseline schema snapshot: {exc}",
                    ),
                ),
                severity,
            )

        result = build_result(
            dataset_name=dataset_name,
            check_type=CHECK_TYPE,
            column_name=None,
            rule="baseline_schema_snapshot",
            total_rows=len(current_schema),
            failed_rows=0,
            status="SKIPPED",
            details=make_message_detail(
                dataset_name,
                CHECK_TYPE,
                None,
                "No previous schema snapshot found. Saved current schema as baseline.",
            ),
        )
        result["severity"] = "LOW"
        return result

    changes = compare_schema_snapshots(current_schema, previous_schema)

    snapshot_save_error = None
    try:
        save_schema_snapshot(run_id, dataset_name, current_schema)
    except Exception as exc:
        snapshot_save_error = exc
        logger.exception("Could not save schema snapshot for %s.", dataset_name)

    failed_rows = len(changes)
    if snapshot_save_error:
        failed_rows = max(failed_rows, 1)

    status = "FAIL" if changes else "PASS"
    details = _schema_change_details(dataset_name, changes)
    if snapshot_save_error:
        status = "FAIL"
        details.extend(
            make_message_detail(
                dataset_name,
                CHECK_TYPE,
                None,
                f"Could not save current schema snapshot: {snapshot_save_error}",
            )
        )

    result = build_result(
        dataset_name=dataset_name,
        check_type=CHECK_TYPE,
        column_name=None,
        rule="compare_current_schema_to_previous_snapshot",
        total_rows=max(len(current_schema), len(previous_schema), 1),
        failed_rows=failed_rows,
        status=status,
        details=details,
    )

    if status == "FAIL":
        result["severity"] = severity

    return result


def normalize_schema(schema_df: pd.DataFrame) -> list[dict[str, Any]]:
    """Normalize source/snapshot schema rows into comparable dictionaries."""

    if schema_df.empty:
        return []

    rows = []
    for index, row in schema_df.reset_index(drop=True).iterrows():
        column_name = _safe_text(row.get("column_name"))
        if not column_name:
            continue
        rows.append({
            "column_name": column_name,
            "data_type": _safe_text(row.get("data_type")).lower(),
            "is_nullable": _normalize_nullable(row.get("is_nullable")),
            "ordinal_position": _safe_int(
                row.get("ordinal_position"),
                default=index + 1,
            ),
        })

    return rows


def ensure_schema_snapshot_table_exists() -> None:
    """Create the schema snapshot table if it is missing."""

    engine = create_monitor_engine()
    with engine.begin() as connection:
        connection.execute(CREATE_SCHEMA_SNAPSHOT_TABLE_SQL)


def _schema_change_details(
    dataset_name: str,
    changes: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Convert schema changes into issue-detail rows."""

    details = []

    for change in changes:
        reason = _change_reason(change)
        details.append({
            "dataset_name": dataset_name,
            "check_type": CHECK_TYPE,
            "column_name": change.get("column_name"),
            "row_identifier": "schema_level",
            "bad_value": str(change.get("current_value") or change.get("change_type")),
            "reason": reason,
            "sample_row": json.dumps(change, default=str, sort_keys=True),
        })

    return details


def _change(
    change_type: str,
    column_name: str,
    previous_schema: dict[str, Any] | None,
    current_schema: dict[str, Any] | None,
    previous_value: Any | None = None,
    current_value: Any | None = None,
) -> dict[str, Any]:
    """Build one schema-change payload."""

    return {
        "change_type": change_type,
        "column_name": column_name,
        "previous_schema": previous_schema,
        "current_schema": current_schema,
        "previous_value": previous_value,
        "current_value": current_value,
    }


def _change_reason(change: dict[str, Any]) -> str:
    """Return a readable reason for one schema drift change."""

    change_type = change.get("change_type")
    column_name = change.get("column_name")

    if change_type == "added_column":
        return f"Column '{column_name}' was added to the source schema."
    if change_type == "removed_column":
        return f"Column '{column_name}' was removed from the source schema."
    if change_type == "changed_data_type":
        return (
            f"Column '{column_name}' data type changed from "
            f"{change.get('previous_value')} to {change.get('current_value')}."
        )
    if change_type == "changed_nullability":
        return (
            f"Column '{column_name}' nullability changed from "
            f"{change.get('previous_value')} to {change.get('current_value')}."
        )
    if change_type == "changed_column_order":
        return (
            f"Column '{column_name}' ordinal position changed from "
            f"{change.get('previous_value')} to {change.get('current_value')}."
        )
    return f"Column '{column_name}' has schema drift: {change_type}."


def _result_with_severity(result: dict[str, Any], severity: str) -> dict[str, Any]:
    """Override severity on a standardized result."""

    result["severity"] = severity
    return result


def _enabled(config: dict[str, Any]) -> bool:
    """Return whether schema drift detection is enabled."""

    return bool(config.get("enabled", False)) if isinstance(config, dict) else False


def _safe_text(value: Any) -> str:
    """Convert optional metadata values to comparable text."""

    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    return str(value).strip()


def _normalize_nullable(value: Any) -> str:
    """Normalize nullable metadata values."""

    text_value = _safe_text(value).upper()
    if text_value in {"YES", "TRUE", "1"}:
        return "YES"
    if text_value in {"NO", "FALSE", "0"}:
        return "NO"
    return text_value or "UNKNOWN"


def _safe_int(value: Any, default: int) -> int:
    """Convert metadata values to int with a default."""

    try:
        if pd.isna(value):
            return default
    except (TypeError, ValueError):
        pass

    try:
        return int(value)
    except (TypeError, ValueError):
        return default
