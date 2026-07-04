from alerts.alert_manager import create_alerts_for_run
from checks.anomaly_checks import run_statistical_checks
from checks.rule_engine import run_rules_for_dataset
from config.rule_loader import load_rules
from data_sources.postgres_connector import get_table_names, load_table
from reports.data_profiler import profile_and_save_datasets
from reports.generate_report import save_results_to_postgres
from reports.quality_score import calculate_quality_score
from utils.logger import get_logger
from notifications.mailtrap_notifier import send_mailtrap_alert_email
logger = get_logger(__name__)


def main():
    """Run configured data quality checks and save the results."""

    logger.info("Starting automated data quality monitoring run.")

    rules = load_rules("config/rules.yaml")
    logger.info("Loaded data quality rules from config/rules.yaml.")
    global_rules = rules.get("global_rules", {})

    available_tables = get_table_names()
    logger.info("Found %s table(s) in PostgreSQL.", len(available_tables))

    ignored_sections = {
        "global_rules",
        "cross_table_validations",
        "quality_thresholds",
    }

    all_results = []
    loaded_datasets = {}

    for dataset_name, dataset_rules in rules.items():
        if dataset_name in ignored_sections:
            continue

        if dataset_name not in available_tables:
            logger.warning(
                "Skipping %s: table does not exist in PostgreSQL.",
                dataset_name,
            )
            continue

        logger.info("Running checks for table: %s", dataset_name)

        df = load_table(dataset_name)
        loaded_datasets[dataset_name] = df

        dataset_results = run_rules_for_dataset(
            df=df,
            dataset_name=dataset_name,
            dataset_rules=dataset_rules,
            table_loader=load_table,
        )
        all_results.extend(dataset_results)

        statistical_results = run_statistical_checks(
            df=df,
            dataset_name=dataset_name,
            global_rules=global_rules,
        )
        all_results.extend(statistical_results)

        logger.info(
            "Completed %s rule check(s) and %s statistical check(s) for table: %s",
            len(dataset_results),
            len(statistical_results),
            dataset_name,
        )

    for result in all_results:
        logger.debug("Data quality check result: %s", result)

    quality_score = calculate_quality_score(all_results)
    failed_checks = [r for r in all_results if r["status"] == "FAIL"]

    logger.info("Total checks: %s", len(all_results))
    logger.info("Quality score: %s%%", quality_score)

    if failed_checks:
        logger.warning("Overall status: FAIL (%s failed check(s)).", len(failed_checks))
    else:
        logger.info("Overall status: PASS")

    save_result = save_results_to_postgres(all_results)

    run_id = save_result["run_id"]
    summary = save_result["summary"]

    try:
        saved_profile_count = profile_and_save_datasets(run_id, loaded_datasets)
        logger.info(
            "Saved %s data profile result(s) for run %s.",
            saved_profile_count,
            run_id,
        )
    except Exception:
        logger.exception("Data profiling failed for run %s.", run_id)

    created_alerts = create_alerts_for_run(run_id, summary)

    send_mailtrap_alert_email(
        run_id=run_id,
        summary=summary,
        alerts=created_alerts
    )
    logger.info("Data quality monitoring run completed. Run ID: %s", run_id)


if __name__ == "__main__":
    main()
