from typing import Any

from sqlalchemy import text

from data_sources.postgres_connector import create_postgres_engine
from utils.logger import get_logger


logger = get_logger(__name__)


RESULT_INSERT_SQL = """
    INSERT INTO data_quality_results (
        run_id,
        dataset_name,
        check_type,
        column_name,
        rule,
        total_rows,
        failed_rows,
        failure_rate,
        status,
        severity
    )
    VALUES (
        :run_id,
        :dataset_name,
        :check_type,
        :column_name,
        :rule,
        :total_rows,
        :failed_rows,
        :failure_rate,
        :status,
        :severity
    )
    RETURNING id
"""


DETAIL_INSERT_SQL = """
    INSERT INTO data_quality_issue_details (
        run_id,
        result_id,
        dataset_name,
        check_type,
        column_name,
        row_identifier,
        bad_value,
        reason,
        sample_row
    )
    VALUES (
        :run_id,
        :result_id,
        :dataset_name,
        :check_type,
        :column_name,
        :row_identifier,
        :bad_value,
        :reason,
        :sample_row
    )
"""


def calculate_run_summary(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Calculate run-level totals and quality score from check results."""

    valid_results = [
        result for result in results
        if result.get("status") in ["PASS", "FAIL"]
    ]

    total_checks = len(valid_results)
    passed_checks = sum(1 for r in valid_results if r.get("status") == "PASS")
    failed_checks = sum(1 for r in valid_results if r.get("status") == "FAIL")
    critical_checks = sum(1 for r in valid_results if r.get("severity") == "CRITICAL")

    quality_score = 0

    if total_checks > 0:
        quality_score = round((passed_checks / total_checks) * 100, 2)

    overall_status = "PASS" if failed_checks == 0 else "FAIL"

    return {
        "total_checks": total_checks,
        "passed_checks": passed_checks,
        "failed_checks": failed_checks,
        "critical_checks": critical_checks,
        "quality_score": quality_score,
        "overall_status": overall_status,
    }


def _insert_result_rows(connection, run_id: int, results: list[dict[str, Any]]) -> int:
    """Insert check results and issue details for an existing run."""

    result_insert_query = text(RESULT_INSERT_SQL)
    detail_insert_query = text(DETAIL_INSERT_SQL)
    inserted_count = 0

    for result in results:
        result_params = {
            "run_id": run_id,
            "dataset_name": result.get("dataset_name"),
            "check_type": result.get("check_type"),
            "column_name": result.get("column"),
            "rule": str(result.get("rule", "")),
            "total_rows": int(result.get("total_rows", 0)),
            "failed_rows": int(result.get("failed_rows", 0)),
            "failure_rate": float(result.get("failure_rate", 0)),
            "status": result.get("status"),
            "severity": result.get("severity", "NONE"),
        }

        result_id = connection.execute(result_insert_query, result_params).scalar()
        inserted_count += 1
        logger.debug(
            "Saved result %s for dataset=%s check_type=%s status=%s.",
            result_id,
            result_params["dataset_name"],
            result_params["check_type"],
            result_params["status"],
        )

        for detail in result.get("details", []):
            detail_params = {
                "run_id": run_id,
                "result_id": result_id,
                "dataset_name": detail.get("dataset_name"),
                "check_type": detail.get("check_type"),
                "column_name": detail.get("column_name"),
                "row_identifier": detail.get("row_identifier"),
                "bad_value": detail.get("bad_value"),
                "reason": detail.get("reason"),
                "sample_row": detail.get("sample_row"),
            }

            connection.execute(detail_insert_query, detail_params)

    return inserted_count


def update_run_summary(run_id: int, results: list[dict[str, Any]]) -> dict[str, Any]:
    """Recalculate and update the summary row for an existing run."""

    summary = calculate_run_summary(results)
    update_query = text("""
        UPDATE data_quality_runs
        SET
            total_checks = :total_checks,
            passed_checks = :passed_checks,
            failed_checks = :failed_checks,
            critical_checks = :critical_checks,
            quality_score = :quality_score,
            overall_status = :overall_status
        WHERE run_id = :run_id
    """)
    params = {"run_id": run_id, **summary}
    engine = create_postgres_engine()

    with engine.begin() as connection:
        connection.execute(update_query, params)

    logger.info("Updated data quality run summary for run %s: %s", run_id, summary)
    return summary


def append_results_to_existing_run(
    run_id: int,
    results: list[dict[str, Any]],
) -> int:
    """Append additional result rows to an existing data quality run."""

    if not results:
        logger.info("No additional data quality results to append for run %s.", run_id)
        return 0

    engine = create_postgres_engine()

    with engine.begin() as connection:
        inserted_count = _insert_result_rows(connection, run_id, results)

    logger.info("Appended %s result(s) to data quality run %s.", inserted_count, run_id)
    return inserted_count


def save_results_to_postgres(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Persist run summary, check results, and issue details to PostgreSQL."""

    logger.info("Saving %s data quality result(s) to PostgreSQL.", len(results))

    engine = create_postgres_engine()

    summary = calculate_run_summary(results)
    logger.info("Calculated run summary: %s", summary)

    with engine.begin() as connection:
        run_insert_query = text("""
            INSERT INTO data_quality_runs (
                total_checks,
                passed_checks,
                failed_checks,
                critical_checks,
                quality_score,
                overall_status
            )
            VALUES (
                :total_checks,
                :passed_checks,
                :failed_checks,
                :critical_checks,
                :quality_score,
                :overall_status
            )
            RETURNING run_id
        """)

        run_id = connection.execute(run_insert_query, summary).scalar()
        logger.info("Created data quality run record. Run ID: %s", run_id)

        _insert_result_rows(connection, run_id, results)

    logger.info("Data quality run saved successfully. Run ID: %s", run_id)
    return {
        "run_id": run_id,
        "summary": summary
    }
