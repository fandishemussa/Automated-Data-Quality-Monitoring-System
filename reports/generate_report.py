import pandas as pd
from sqlalchemy import text
from data_sources.postgres_connector import create_postgres_engine


def calculate_run_summary(results):
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
        "overall_status": overall_status
    }




def save_results_to_postgres(results):
    engine = create_postgres_engine()

    summary = calculate_run_summary(results)

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

        result_insert_query = text("""
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
        """)

        detail_insert_query = text("""
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
        """)

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

            result_id = connection.execute(
                result_insert_query,
                result_params
            ).scalar()

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

    print(f"Data quality run saved successfully. Run ID: {run_id}")