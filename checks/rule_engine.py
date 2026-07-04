import re
import pandas as pd

def calculate_severity(check_type, status, failure_rate):
    if status == "PASS":
        return "NONE"

    if status == "SKIPPED":
        return "LOW"

    critical_checks = [
        "required_column_check",
        "referential_integrity_check"
    ]

    high_checks = [
        "not_null_check",
        "unique_check"
    ]

    medium_checks = [
        "format_check",
        "range_check",
        "categorical_check",
        "freshness_check",
        "custom_email_domain_check"
    ]

    if check_type in critical_checks:
        return "CRITICAL"

    if check_type in high_checks:
        if failure_rate >= 0.20:
            return "CRITICAL"
        return "HIGH"

    if check_type in medium_checks:
        if failure_rate >= 0.50:
            return "HIGH"
        if failure_rate >= 0.10:
            return "MEDIUM"
        return "LOW"

    return "MEDIUM"
def safe_text(value):
    if value is None:
        return None

    try:
        if pd.isna(value):
            return None
    except Exception:
        pass

    return str(value)


def make_issue_details(
    failed_df,
    dataset_name,
    check_type,
    column_name,
    reason,
    max_examples=5
):
    details = []

    if failed_df is None or failed_df.empty:
        return details

    possible_id_columns = [
        "id",
        "customer_id",
        "order_id",
        "product_id"
    ]

    for index, row in failed_df.head(max_examples).iterrows():
        row_identifier = f"row_index={index}"

        for id_column in possible_id_columns:
            if id_column in failed_df.columns:
                row_identifier = f"{id_column}={safe_text(row[id_column])}"
                break

        sample_row = {
            col: safe_text(row[col])
            for col in failed_df.columns
        }

        details.append({
            "dataset_name": dataset_name,
            "check_type": check_type,
            "column_name": column_name,
            "row_identifier": row_identifier,
            "bad_value": safe_text(row[column_name]) if column_name in failed_df.columns else None,
            "reason": reason,
            "sample_row": str(sample_row)
        })

    return details
def build_result(
    dataset_name,
    check_type,
    column_name=None,
    rule=None,
    total_rows=0,
    failed_rows=0,
    status="PASS",
    details=None
):
    failure_rate = 0

    if total_rows > 0:
        failure_rate = round(float(failed_rows / total_rows), 4)

    severity = calculate_severity(check_type, status, failure_rate)

    return {
        "dataset_name": dataset_name,
        "check_type": check_type,
        "column": column_name,
        "rule": rule,
        "total_rows": int(total_rows),
        "failed_rows": int(failed_rows),
        "failure_rate": failure_rate,
        "status": status,
        "severity": severity,
        "details": details or []
    }

def check_required_columns(df, dataset_name, required_columns):
    results = []
    existing_columns = df.columns.tolist()

    for column in required_columns:
        failed_rows = 0 if column in existing_columns else 1
        status = "PASS" if column in existing_columns else "FAIL"

        results.append(
            build_result(
                dataset_name=dataset_name,
                check_type="required_column_check",
                column_name=column,
                rule="column_must_exist",
                total_rows=1,
                failed_rows=failed_rows,
                status=status
            )
        )

    return results


def check_not_null_columns(df, dataset_name, columns):
    results = []
    total_rows = len(df)

    for column in columns:
        if column not in df.columns:
            results.append(
                build_result(
                    dataset_name,
                    "not_null_check",
                    column,
                    "column_missing",
                    total_rows,
                    total_rows,
                    "FAIL"
                )
            )
            continue

        failed_df = df[df[column].isnull()]
        failed_rows = len(failed_df)
        status = "PASS" if failed_rows == 0 else "FAIL"

        details = make_issue_details(
            failed_df,
            dataset_name,
            "not_null_check",
            column,
            f"{column} must not be null"
        )

        results.append(
            build_result(
                dataset_name,
                "not_null_check",
                column,
                "not_null",
                total_rows,
                failed_rows,
                status,
                details
            )
        )

    return results
def check_unique_columns(df, dataset_name, columns):
    results = []
    total_rows = len(df)

    for column in columns:
        if column not in df.columns:
            results.append(
                build_result(
                    dataset_name,
                    "unique_check",
                    column,
                    "column_missing",
                    total_rows,
                    total_rows,
                    "FAIL"
                )
            )
            continue

        failed_rows = df[column].duplicated().sum()
        status = "PASS" if failed_rows == 0 else "FAIL"

        results.append(
            build_result(
                dataset_name,
                "unique_check",
                column,
                "unique",
                total_rows,
                failed_rows,
                status
            )
        )

    return results


def check_format_rules(df, dataset_name, format_checks):
    results = []
    total_rows = len(df)

    patterns = {
        "email": r"^[\w\.-]+@[\w\.-]+\.\w+$",
        "alpha_with_spaces": r"^[A-Za-z\s]+$",
        "alphanumeric_with_spaces_and_hyphens": r"^[A-Za-z0-9\s\-]+$"
    }

    for column, format_type in format_checks.items():
        if column not in df.columns:
            results.append(
                build_result(
                    dataset_name,
                    "format_check",
                    column,
                    "column_missing",
                    total_rows,
                    total_rows,
                    "FAIL"
                )
            )
            continue

        pattern = patterns.get(format_type)

        if pattern is None:
            results.append(
                build_result(
                    dataset_name,
                    "format_check",
                    column,
                    f"unsupported_format:{format_type}",
                    total_rows,
                    0,
                    "SKIPPED"
                )
            )
            continue

        non_null_df = df[df[column].notnull()]

        failed_df = non_null_df[
            ~non_null_df[column].astype(str).str.contains(pattern, regex=True, na=False)
        ]

        failed_rows = len(failed_df)
        status = "PASS" if failed_rows == 0 else "FAIL"

        details = make_issue_details(
            failed_df,
            dataset_name,
            "format_check",
            column,
            f"{column} must match format: {format_type}"
        )

        results.append(
            build_result(
                dataset_name,
                "format_check",
                column,
                format_type,
                total_rows,
                failed_rows,
                status,
                details
            )
        )

    return results

def check_range_rules(df, dataset_name, range_checks):
    results = []
    total_rows = len(df)

    for column, rules in range_checks.items():
        if column not in df.columns:
            results.append(
                build_result(
                    dataset_name,
                    "range_check",
                    column,
                    "column_missing",
                    total_rows,
                    total_rows,
                    "FAIL"
                )
            )
            continue

        failed_mask = pd.Series(False, index=df.index)

        # String length checks
        if "min_length" in rules:
            failed_mask = failed_mask | (df[column].astype(str).str.len() < rules["min_length"])

        if "max_length" in rules:
            failed_mask = failed_mask | (df[column].astype(str).str.len() > rules["max_length"])

        # Numeric range checks
        if "min" in rules:
            failed_mask = failed_mask | (pd.to_numeric(df[column], errors="coerce") < rules["min"])

        if "max" in rules:
            failed_mask = failed_mask | (pd.to_numeric(df[column], errors="coerce") > rules["max"])

        # Date max today check
        if rules.get("max_date") == "today":
            dates = pd.to_datetime(df[column], errors="coerce")
            today = pd.Timestamp.now().normalize()
            failed_mask = failed_mask | (dates > today)

        failed_rows = failed_mask.sum()
        status = "PASS" if failed_rows == 0 else "FAIL"

        results.append(
            build_result(
                dataset_name,
                "range_check",
                column,
                str(rules),
                total_rows,
                failed_rows,
                status
            )
        )

    return results


def check_categorical_rules(df, dataset_name, categorical_checks):
    results = []
    total_rows = len(df)

    for column, rule_config in categorical_checks.items():
        if column not in df.columns:
            results.append(
                build_result(
                    dataset_name,
                    "categorical_check",
                    column,
                    "column_missing",
                    total_rows,
                    total_rows,
                    "FAIL"
                )
            )
            continue

        allowed_values = rule_config.get("allowed_values", [])

        invalid_rows = df[
            df[column].notnull() & ~df[column].isin(allowed_values)
        ]

        failed_rows = len(invalid_rows)
        status = "PASS" if failed_rows == 0 else "FAIL"

        results.append(
            build_result(
                dataset_name,
                "categorical_check",
                column,
                "allowed_values",
                total_rows,
                failed_rows,
                status
            )
        )

    return results


def check_freshness_rules(df, dataset_name, freshness_rules):
    results = []
    total_rows = len(df)

    for column, rule_config in freshness_rules.items():
        if column not in df.columns:
            results.append(
                build_result(
                    dataset_name,
                    "freshness_check",
                    column,
                    "column_missing",
                    total_rows,
                    total_rows,
                    "FAIL"
                )
            )
            continue

        max_delay_days = rule_config.get("max_delay_days")
        dates = pd.to_datetime(df[column], errors="coerce")

        latest_date = dates.max()

        if pd.isna(latest_date):
            results.append(
                build_result(
                    dataset_name,
                    "freshness_check",
                    column,
                    f"max_delay_days:{max_delay_days}",
                    total_rows,
                    total_rows,
                    "FAIL"
                )
            )
            continue

        delay_days = (pd.Timestamp.now() - latest_date).days

        failed_rows = 0 if delay_days <= max_delay_days else total_rows
        status = "PASS" if failed_rows == 0 else "FAIL"

        results.append(
            build_result(
                dataset_name,
                "freshness_check",
                column,
                f"max_delay_days:{max_delay_days}",
                total_rows,
                failed_rows,
                status
            )
        )

    return results
def check_custom_rules(df, dataset_name, custom_rules):
    results = []
    total_rows = len(df)

    # Email domain validation
    if "email_domains" in custom_rules:
        allowed_domains = custom_rules["email_domains"].get("allowed_domains", [])
        column = "email"

        if column not in df.columns:
            results.append(
                build_result(
                    dataset_name,
                    "custom_email_domain_check",
                    column,
                    "email_column_missing",
                    total_rows,
                    total_rows,
                    "FAIL"
                )
            )
            return results

        # Only check non-null and valid-looking emails
        email_pattern = r"^[\w\.-]+@[\w\.-]+\.\w+$"
        non_null_df = df[df[column].notnull()].copy()

        valid_email_df = non_null_df[
            non_null_df[column].astype(str).str.contains(email_pattern, regex=True)
        ].copy()

        valid_email_df["email_domain"] = (
            valid_email_df[column]
            .astype(str)
            .str.split("@")
            .str[-1]
            .str.lower()
        )

        invalid_domain_rows = valid_email_df[
            ~valid_email_df["email_domain"].isin(allowed_domains)
        ]

        failed_rows = len(invalid_domain_rows)
        status = "PASS" if failed_rows == 0 else "FAIL"

        results.append(
            build_result(
                dataset_name,
                "custom_email_domain_check",
                column,
                f"allowed_domains:{allowed_domains}",
                total_rows,
                failed_rows,
                status
            )
        )

    return results

def run_rules_for_dataset(df, dataset_name, dataset_rules, table_loader=None):
    results = []

    if "required_columns" in dataset_rules:
        results.extend(
            check_required_columns(
                df,
                dataset_name,
                dataset_rules["required_columns"]
            )
        )

    if "not_null_columns" in dataset_rules:
        results.extend(
            check_not_null_columns(
                df,
                dataset_name,
                dataset_rules["not_null_columns"]
            )
        )

    if "unique_columns" in dataset_rules:
        results.extend(
            check_unique_columns(
                df,
                dataset_name,
                dataset_rules["unique_columns"]
            )
        )

    if "format_checks" in dataset_rules:
        results.extend(
            check_format_rules(
                df,
                dataset_name,
                dataset_rules["format_checks"]
            )
        )

    if "range_checks" in dataset_rules:
        results.extend(
            check_range_rules(
                df,
                dataset_name,
                dataset_rules["range_checks"]
            )
        )

    if "categorical_checks" in dataset_rules:
        results.extend(
            check_categorical_rules(
                df,
                dataset_name,
                dataset_rules["categorical_checks"]
            )
        )

    if "freshness" in dataset_rules:
        results.extend(
            check_freshness_rules(
                df,
                dataset_name,
                dataset_rules["freshness"]
            )
        )
    if "referential_integrity" in dataset_rules and table_loader is not None:
        results.extend(
            check_referential_integrity(
                df,
                dataset_name,
                dataset_rules["referential_integrity"],
                table_loader
            )
        )
    if "custom_rules" in dataset_rules:
        results.extend(
            check_custom_rules(
                df,
                dataset_name,
                dataset_rules["custom_rules"]
            )
        )
    return results
def check_referential_integrity(df, dataset_name, referential_rules, table_loader):
    results = []
    total_rows = len(df)

    for column, rule_config in referential_rules.items():
        foreign_table = rule_config.get("foreign_table")
        foreign_column = rule_config.get("foreign_column")

        if column not in df.columns:
            results.append(
                build_result(
                    dataset_name,
                    "referential_integrity_check",
                    column,
                    "source_column_missing",
                    total_rows,
                    total_rows,
                    "FAIL"
                )
            )
            continue

        try:
            foreign_df = table_loader(foreign_table)
        except Exception:
            results.append(
                build_result(
                    dataset_name,
                    "referential_integrity_check",
                    column,
                    f"foreign_table_missing:{foreign_table}",
                    total_rows,
                    total_rows,
                    "FAIL"
                )
            )
            continue

        if foreign_column not in foreign_df.columns:
            results.append(
                build_result(
                    dataset_name,
                    "referential_integrity_check",
                    column,
                    f"foreign_column_missing:{foreign_column}",
                    total_rows,
                    total_rows,
                    "FAIL"
                )
            )
            continue

        valid_values = set(foreign_df[foreign_column].dropna())

        failed_df = df[
            df[column].notnull() & ~df[column].isin(valid_values)
        ]

        failed_rows = len(failed_df)
        status = "PASS" if failed_rows == 0 else "FAIL"

        details = make_issue_details(
            failed_df,
            dataset_name,
            "referential_integrity_check",
            column,
            f"{column} must exist in {foreign_table}.{foreign_column}"
        )

        results.append(
            build_result(
                dataset_name,
                "referential_integrity_check",
                column,
                f"{column}_must_exist_in_{foreign_table}.{foreign_column}",
                total_rows,
                failed_rows,
                status,
                details
            )
        )

    return results