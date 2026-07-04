from config.rule_loader import load_rules
from data_sources.postgres_connector import load_table, get_table_names
from checks.rule_engine import run_rules_for_dataset
from reports.generate_report import save_results_to_postgres
from reports.quality_score import calculate_quality_score


def main():
    rules = load_rules("config/rules.yaml")

    available_tables = get_table_names()

    ignored_sections = {
        "global_rules",
        "cross_table_validations",
        "quality_thresholds"
    }

    all_results = []

    for dataset_name, dataset_rules in rules.items():
        if dataset_name in ignored_sections:
            continue

        if dataset_name not in available_tables:
            print(f"⚠️ Skipping {dataset_name}: table does not exist in PostgreSQL.")
            continue

        print(f"\n🚀 Running checks for table: {dataset_name}")

        df = load_table(dataset_name)

        dataset_results = run_rules_for_dataset(
            df=df,
            dataset_name=dataset_name,
            dataset_rules=dataset_rules,
            table_loader=load_table
        )
        all_results.extend(dataset_results)

    print("\n--- Data Quality Results ---")
    for result in all_results:
        print(result)

    quality_score = calculate_quality_score(all_results)

    print("\n--- Summary ---")
    print("Total checks:", len(all_results))
    print("Quality Score:", quality_score, "%")

    failed_checks = [r for r in all_results if r["status"] == "FAIL"]

    if failed_checks:
        print("Overall Status: FAIL")
    else:
        print("Overall Status: PASS")

    save_results_to_postgres(all_results)


if __name__ == "__main__":
    main()