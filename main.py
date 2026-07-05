from alerts.alert_manager import create_alerts_for_run
from checks.anomaly_checks import run_statistical_checks
from checks.drift_detection import run_advanced_drift_checks_for_datasets
from checks.rule_engine import run_rules_for_dataset
from config.rule_loader import load_rules
from config.settings import get_bool_env
from data_sources.source_factory import get_source_functions, get_source_type
from notifications.mailtrap_notifier import send_mailtrap_alert_email
from notifications.slack_notifier import send_slack_alert
from notifications.teams_notifier import send_teams_alert
from reports.data_profiler import profile_and_save_datasets
from reports.generate_report import (
    append_results_to_existing_run,
    save_results_to_postgres,
    update_run_summary,
)
from reports.quality_score import calculate_quality_score
from sla.sla_checker import evaluate_sla_for_run, save_sla_results
from utils.config_validator import has_failures, print_validation_report, validate_config
from utils.logger import get_logger
logger = get_logger(__name__)

CRITICAL_PREFLIGHT_CHECKS = {
    "rules.yaml exists",
    "rules.yaml valid",
    "source database connection",
    "monitoring database connection",
    "monitoring tables",
    "source tables referenced in rules",
}


def run_preflight_checks() -> bool:
    """Validate required runtime configuration before starting a run."""

    if get_bool_env("SKIP_PREFLIGHT_CHECK", False):
        logger.warning("Skipping preflight checks because SKIP_PREFLIGHT_CHECK=true.")
        return True

    logger.info("Running preflight configuration checks.")
    validation_results = validate_config()

    if has_failures(validation_results, CRITICAL_PREFLIGHT_CHECKS):
        print_validation_report(validation_results)
        logger.error("Preflight validation failed. Monitoring run was not started.")
        print("")
        print("Preflight failed. Useful commands:")
        print("python cli.py validate-config")
        print("python cli.py init-db")
        return False

    warnings = [
        result for result in validation_results
        if result["status"] == "WARNING"
    ]
    if warnings:
        logger.warning("Preflight completed with %s warning(s).", len(warnings))
    else:
        logger.info("Preflight validation passed.")

    return True


def main():
    """Run configured data quality checks and save the results."""

    logger.info("Starting automated data quality monitoring run.")

    if not run_preflight_checks():
        return

    rules = load_rules("config/rules.yaml")
    logger.info("Loaded data quality rules from config/rules.yaml.")
    global_rules = rules.get("global_rules", {})

    source = get_source_functions()
    load_table = source.load_table
    get_table_names = source.get_table_names
    source_type = get_source_type()

    available_tables = get_table_names()
    logger.info(
        "Found %s table(s) in configured source database: %s.",
        len(available_tables),
        source_type,
    )

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

    drift_results = run_advanced_drift_checks_for_datasets(
        datasets=loaded_datasets,
        global_rules=global_rules,
        current_run_id=run_id,
    )

    if drift_results:
        append_results_to_existing_run(run_id, drift_results)
        all_results.extend(drift_results)
        summary = update_run_summary(run_id, all_results)
        logger.info(
            "Saved %s advanced drift result(s) for run %s.",
            len(drift_results),
            run_id,
        )

    try:
        sla_results = evaluate_sla_for_run(run_id, all_results)
        saved_sla_count = save_sla_results(sla_results)
        logger.info(
            "Saved %s SLA tracking result(s) for run %s.",
            saved_sla_count,
            run_id,
        )
    except Exception:
        logger.exception("SLA evaluation failed for run %s.", run_id)

    created_alerts = create_alerts_for_run(run_id, summary, all_results)

    send_mailtrap_alert_email(
        run_id=run_id,
        summary=summary,
        alerts=created_alerts
    )
    send_slack_alert(
        run_id=run_id,
        summary=summary,
        alerts=created_alerts,
    )
    send_teams_alert(
        run_id=run_id,
        summary=summary,
        alerts=created_alerts,
    )
    logger.info("Data quality monitoring run completed. Run ID: %s", run_id)


if __name__ == "__main__":
    main()
