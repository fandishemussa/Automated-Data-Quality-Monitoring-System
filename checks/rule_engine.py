"""Rule execution engine for dataset-level data quality checks.

The public entry point is `run_rules_for_dataset`, which receives a DataFrame,
the dataset name, and the rule configuration for that dataset. Each check
returns a standardized result dictionary that can be saved by the reporting
module.
"""

from typing import Any, Callable

import pandas as pd

from utils.logger import get_logger


logger = get_logger(__name__)

DEFAULT_MAX_DETAIL_EXAMPLES = 5

FORMAT_PATTERNS = {
    "email": r"^[\w\.-]+@[\w\.-]+\.\w+$",
    "alpha_with_spaces": r"^[A-Za-z\s]+$",
    "alphanumeric_with_spaces_and_hyphens": r"^[A-Za-z0-9\s\-]+$",
}

ID_COLUMNS_BY_DATASET = {
    "customers": ["customer_id", "id"],
    "orders": ["order_id", "id", "customer_id"],
    "products": ["product_id", "id"],
}

DEFAULT_ID_COLUMNS = ["id", "customer_id", "order_id", "product_id"]


def calculate_severity(check_type, status, failure_rate):
    """Calculate a severity label for a standardized check result."""

    if status == "PASS":
        return "NONE"

    if status == "SKIPPED":
        return "LOW"

    critical_checks = [
        "required_column_check",
        "referential_integrity_check",
        "rule_execution_error",
    ]

    high_checks = [
        "not_null_check",
        "unique_check",
    ]

    medium_checks = [
        "format_check",
        "range_check",
        "categorical_check",
        "freshness_check",
        "custom_email_domain_check",
        "z_score_anomaly_check",
        "data_drift_check",
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
    """Convert a value to safe text for issue details."""

    if value is None:
        return "NULL"

    try:
        if pd.isna(value):
            return "NULL"
    except (TypeError, ValueError):
        pass

    return str(value)


def _total_rows(df):
    """Return a safe row count for a DataFrame-like object."""

    return len(df) if isinstance(df, pd.DataFrame) else 0


def _failure_rate(total_rows, failed_rows):
    """Calculate failure rate while keeping missing-table failures visible."""

    if total_rows > 0:
        return round(float(failed_rows / total_rows), 4)

    return 1.0 if failed_rows > 0 else 0


def _status_from_failed_rows(failed_rows):
    """Return PASS when no rows failed; otherwise FAIL."""

    return "PASS" if failed_rows == 0 else "FAIL"


def _possible_id_columns(dataset_name):
    """Return likely row identifier columns for a dataset."""

    return ID_COLUMNS_BY_DATASET.get(dataset_name, DEFAULT_ID_COLUMNS)


def _row_identifier(row, row_index, dataset_name, columns):
    """Build a human-readable row identifier for issue details."""

    for id_column in _possible_id_columns(dataset_name):
        if id_column in columns:
            return f"{id_column}={safe_text(row[id_column])}"

    return f"row_index={row_index}"


def _sample_row(row, columns):
    """Serialize a row sample for storage in the issue details table."""

    return {
        column: safe_text(row[column])
        for column in columns
    }


def make_issue_details(
    failed_df,
    dataset_name,
    check_type,
    column_name,
    reason,
    max_examples=DEFAULT_MAX_DETAIL_EXAMPLES,
):
    """Create example issue-detail records from failed rows when available."""

    details = []

    if failed_df is None or failed_df.empty:
        return details

    columns = failed_df.columns.tolist()

    for index, row in failed_df.head(max_examples).iterrows():
        details.append({
            "dataset_name": dataset_name,
            "check_type": check_type,
            "column_name": column_name,
            "row_identifier": _row_identifier(row, index, dataset_name, columns),
            "bad_value": (
                safe_text(row[column_name])
                if column_name in columns
                else "NULL"
            ),
            "reason": reason,
            "sample_row": str(_sample_row(row, columns)),
        })

    return details


def make_message_detail(dataset_name, check_type, column_name, reason):
    """Create a detail record for failures that do not have row examples."""

    return [{
        "dataset_name": dataset_name,
        "check_type": check_type,
        "column_name": column_name,
        "row_identifier": "table_level",
        "bad_value": "NULL",
        "reason": reason,
        "sample_row": "{}",
    }]


def build_result(
    dataset_name,
    check_type,
    column_name=None,
    rule=None,
    total_rows=0,
    failed_rows=0,
    status=None,
    details=None,
):
    """Build the standardized result dictionary used throughout the project."""

    if status is None:
        status = _status_from_failed_rows(failed_rows)

    failure_rate = _failure_rate(total_rows, failed_rows)
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
        "details": details or [],
    }


def _build_failure_result(
    dataset_name,
    check_type,
    column_name,
    rule,
    total_rows,
    reason,
    failed_rows=None,
):
    """Build a FAIL result for missing columns, bad configs, or exceptions."""

    if failed_rows is None:
        failed_rows = total_rows if total_rows > 0 else 1

    return build_result(
        dataset_name=dataset_name,
        check_type=check_type,
        column_name=column_name,
        rule=rule,
        total_rows=total_rows,
        failed_rows=failed_rows,
        status="FAIL",
        details=make_message_detail(dataset_name, check_type, column_name, reason),
    )


def _column_missing_result(df, dataset_name, check_type, column_name, rule):
    """Build a consistent failure result for missing columns."""

    reason = f"Required column '{column_name}' is missing from {dataset_name}."
    return _build_failure_result(
        dataset_name=dataset_name,
        check_type=check_type,
        column_name=column_name,
        rule=rule,
        total_rows=_total_rows(df),
        reason=reason,
    )


def _ensure_rule_mapping(rules, rule_group_name):
    """Validate that a rule group is a mapping."""

    if not isinstance(rules, dict):
        raise ValueError(f"{rule_group_name} must be a mapping of column names to rules.")


def _ensure_rule_list(rules, rule_group_name):
    """Validate that a rule group is a list."""

    if not isinstance(rules, list):
        raise ValueError(f"{rule_group_name} must be a list of column names.")


def _non_null_values(df, column):
    """Return rows where the selected column is not null."""

    return df[df[column].notnull()]


def check_required_columns(df, dataset_name, required_columns):
    """Check that every required column exists in the DataFrame."""

    _ensure_rule_list(required_columns, "required_columns")

    results = []
    existing_columns = set(df.columns)

    for column in required_columns:
        missing = column not in existing_columns
        details = []

        if missing:
            details = make_message_detail(
                dataset_name,
                "required_column_check",
                column,
                f"Required column '{column}' is missing from {dataset_name}.",
            )

        results.append(
            build_result(
                dataset_name=dataset_name,
                check_type="required_column_check",
                column_name=column,
                rule="column_must_exist",
                total_rows=1,
                failed_rows=1 if missing else 0,
                status="FAIL" if missing else "PASS",
                details=details,
            )
        )

    return results


def check_not_null_columns(df, dataset_name, columns):
    """Check that configured columns do not contain null values."""

    _ensure_rule_list(columns, "not_null_columns")

    results = []
    total_rows = _total_rows(df)

    for column in columns:
        if column not in df.columns:
            results.append(
                _column_missing_result(
                    df,
                    dataset_name,
                    "not_null_check",
                    column,
                    "column_missing",
                )
            )
            continue

        failed_df = df[df[column].isnull()]
        failed_rows = len(failed_df)
        details = make_issue_details(
            failed_df,
            dataset_name,
            "not_null_check",
            column,
            f"{column} must not be null.",
        )

        results.append(
            build_result(
                dataset_name,
                "not_null_check",
                column,
                "not_null",
                total_rows,
                failed_rows,
                details=details,
            )
        )

    return results


def check_unique_columns(df, dataset_name, columns):
    """Check that configured columns contain unique values."""

    _ensure_rule_list(columns, "unique_columns")

    results = []
    total_rows = _total_rows(df)

    for column in columns:
        if column not in df.columns:
            results.append(
                _column_missing_result(
                    df,
                    dataset_name,
                    "unique_check",
                    column,
                    "column_missing",
                )
            )
            continue

        duplicate_mask = df[column].duplicated()
        duplicate_example_mask = df[column].duplicated(keep=False)
        failed_df = df[duplicate_example_mask]
        failed_rows = int(duplicate_mask.sum())
        details = make_issue_details(
            failed_df,
            dataset_name,
            "unique_check",
            column,
            f"{column} must be unique.",
        )

        results.append(
            build_result(
                dataset_name,
                "unique_check",
                column,
                "unique",
                total_rows,
                failed_rows,
                details=details,
            )
        )

    return results


def check_format_rules(df, dataset_name, format_checks):
    """Check configured columns against named regular expression formats."""

    _ensure_rule_mapping(format_checks, "format_checks")

    results = []
    total_rows = _total_rows(df)

    for column, format_type in format_checks.items():
        if column not in df.columns:
            results.append(
                _column_missing_result(
                    df,
                    dataset_name,
                    "format_check",
                    column,
                    "column_missing",
                )
            )
            continue

        pattern = FORMAT_PATTERNS.get(format_type)

        if pattern is None:
            results.append(
                _build_failure_result(
                    dataset_name,
                    "format_check",
                    column,
                    f"unsupported_format:{format_type}",
                    total_rows,
                    f"Unsupported format type '{format_type}' for column '{column}'.",
                    failed_rows=1,
                )
            )
            continue

        non_null_df = _non_null_values(df, column)
        failed_df = non_null_df[
            ~non_null_df[column].astype(str).str.match(pattern, na=False)
        ]
        failed_rows = len(failed_df)
        details = make_issue_details(
            failed_df,
            dataset_name,
            "format_check",
            column,
            f"{column} must match format: {format_type}.",
        )

        results.append(
            build_result(
                dataset_name,
                "format_check",
                column,
                format_type,
                total_rows,
                failed_rows,
                details=details,
            )
        )

    return results


def _build_range_failure_mask(df, column, rules):
    """Return failed rows and reason text for a range rule."""

    failed_mask = pd.Series(False, index=df.index)
    reasons = []

    non_null_mask = df[column].notnull()

    if "min_length" in rules:
        min_length = rules["min_length"]
        failed_mask = failed_mask | (
            non_null_mask & (df[column].astype(str).str.len() < min_length)
        )
        reasons.append(f"minimum length must be {min_length}")

    if "max_length" in rules:
        max_length = rules["max_length"]
        failed_mask = failed_mask | (
            non_null_mask & (df[column].astype(str).str.len() > max_length)
        )
        reasons.append(f"maximum length must be {max_length}")

    has_numeric_rule = "min" in rules or "max" in rules
    numeric_values = pd.to_numeric(df[column], errors="coerce")

    if has_numeric_rule:
        failed_mask = failed_mask | (non_null_mask & numeric_values.isna())
        reasons.append("value must be numeric")

    if "min" in rules:
        min_value = rules["min"]
        failed_mask = failed_mask | (numeric_values < min_value)
        reasons.append(f"minimum value must be {min_value}")

    if "max" in rules:
        max_value = rules["max"]
        failed_mask = failed_mask | (numeric_values > max_value)
        reasons.append(f"maximum value must be {max_value}")

    if rules.get("max_date") == "today":
        dates = pd.to_datetime(df[column], errors="coerce")
        failed_mask = failed_mask | (non_null_mask & dates.isna())
        failed_mask = failed_mask | (dates > pd.Timestamp.now().normalize())
        reasons.append("date must be valid and cannot be in the future")

    return failed_mask, reasons


def check_range_rules(df, dataset_name, range_checks):
    """Check numeric, length, and date range rules."""

    _ensure_rule_mapping(range_checks, "range_checks")

    results = []
    total_rows = _total_rows(df)

    for column, rules in range_checks.items():
        if column not in df.columns:
            results.append(
                _column_missing_result(
                    df,
                    dataset_name,
                    "range_check",
                    column,
                    "column_missing",
                )
            )
            continue

        if not isinstance(rules, dict):
            results.append(
                _build_failure_result(
                    dataset_name,
                    "range_check",
                    column,
                    "invalid_range_rule",
                    total_rows,
                    f"Range rule for '{column}' must be a mapping.",
                    failed_rows=1,
                )
            )
            continue

        failed_mask, reasons = _build_range_failure_mask(df, column, rules)
        failed_df = df[failed_mask]
        failed_rows = len(failed_df)
        reason_text = f"{column} failed range rule: {', '.join(reasons)}."
        details = make_issue_details(
            failed_df,
            dataset_name,
            "range_check",
            column,
            reason_text,
        )

        results.append(
            build_result(
                dataset_name,
                "range_check",
                column,
                str(rules),
                total_rows,
                failed_rows,
                details=details,
            )
        )

    return results


def check_categorical_rules(df, dataset_name, categorical_checks):
    """Check that values are part of configured allowed categories."""

    _ensure_rule_mapping(categorical_checks, "categorical_checks")

    results = []
    total_rows = _total_rows(df)

    for column, rule_config in categorical_checks.items():
        if column not in df.columns:
            results.append(
                _column_missing_result(
                    df,
                    dataset_name,
                    "categorical_check",
                    column,
                    "column_missing",
                )
            )
            continue

        if not isinstance(rule_config, dict):
            results.append(
                _build_failure_result(
                    dataset_name,
                    "categorical_check",
                    column,
                    "invalid_categorical_rule",
                    total_rows,
                    f"Categorical rule for '{column}' must be a mapping.",
                    failed_rows=1,
                )
            )
            continue

        allowed_values = rule_config.get("allowed_values", [])
        failed_df = df[df[column].notnull() & ~df[column].isin(allowed_values)]
        failed_rows = len(failed_df)
        details = make_issue_details(
            failed_df,
            dataset_name,
            "categorical_check",
            column,
            f"{column} must be one of: {allowed_values}.",
        )

        results.append(
            build_result(
                dataset_name,
                "categorical_check",
                column,
                f"allowed_values:{allowed_values}",
                total_rows,
                failed_rows,
                details=details,
            )
        )

    return results


def check_freshness_rules(df, dataset_name, freshness_rules):
    """Check that a date/timestamp column is recent enough."""

    _ensure_rule_mapping(freshness_rules, "freshness")

    results = []
    total_rows = _total_rows(df)

    for column, rule_config in freshness_rules.items():
        if column not in df.columns:
            results.append(
                _column_missing_result(
                    df,
                    dataset_name,
                    "freshness_check",
                    column,
                    "column_missing",
                )
            )
            continue

        if not isinstance(rule_config, dict):
            results.append(
                _build_failure_result(
                    dataset_name,
                    "freshness_check",
                    column,
                    "invalid_freshness_rule",
                    total_rows,
                    f"Freshness rule for '{column}' must be a mapping.",
                    failed_rows=1,
                )
            )
            continue

        max_delay_days = rule_config.get("max_delay_days")

        if max_delay_days is None:
            results.append(
                _build_failure_result(
                    dataset_name,
                    "freshness_check",
                    column,
                    "missing_max_delay_days",
                    total_rows,
                    f"Freshness rule for '{column}' is missing max_delay_days.",
                    failed_rows=1,
                )
            )
            continue

        dates = pd.to_datetime(df[column], errors="coerce")
        invalid_date_df = df[df[column].notnull() & dates.isna()]
        latest_date = dates.max()

        if pd.isna(latest_date):
            details = make_issue_details(
                invalid_date_df if not invalid_date_df.empty else df,
                dataset_name,
                "freshness_check",
                column,
                f"{column} does not contain any valid dates.",
            )
            results.append(
                build_result(
                    dataset_name,
                    "freshness_check",
                    column,
                    f"max_delay_days:{max_delay_days}",
                    total_rows,
                    total_rows if total_rows > 0 else 1,
                    status="FAIL",
                    details=details,
                )
            )
            continue

        delay_days = (pd.Timestamp.now() - latest_date).days
        is_stale = delay_days > max_delay_days
        failed_rows = total_rows if is_stale else len(invalid_date_df)

        if is_stale:
            failed_df = df
            reason = (
                f"Latest {column} is {delay_days} day(s) old; "
                f"maximum allowed delay is {max_delay_days} day(s)."
            )
        else:
            failed_df = invalid_date_df
            reason = f"{column} contains invalid date values."

        details = make_issue_details(
            failed_df,
            dataset_name,
            "freshness_check",
            column,
            reason,
        )

        results.append(
            build_result(
                dataset_name,
                "freshness_check",
                column,
                f"max_delay_days:{max_delay_days}",
                total_rows,
                failed_rows,
                details=details,
            )
        )

    return results


def check_referential_integrity(df, dataset_name, referential_rules, table_loader):
    """Check that local key values exist in a referenced table/column."""

    _ensure_rule_mapping(referential_rules, "referential_integrity")

    results = []
    total_rows = _total_rows(df)

    for column, rule_config in referential_rules.items():
        if not isinstance(rule_config, dict):
            results.append(
                _build_failure_result(
                    dataset_name,
                    "referential_integrity_check",
                    column,
                    "invalid_referential_rule",
                    total_rows,
                    f"Referential integrity rule for '{column}' must be a mapping.",
                    failed_rows=1,
                )
            )
            continue

        foreign_table = rule_config.get("foreign_table")
        foreign_column = rule_config.get("foreign_column")

        if column not in df.columns:
            results.append(
                _column_missing_result(
                    df,
                    dataset_name,
                    "referential_integrity_check",
                    column,
                    "source_column_missing",
                )
            )
            continue

        if not foreign_table or not foreign_column:
            results.append(
                _build_failure_result(
                    dataset_name,
                    "referential_integrity_check",
                    column,
                    "missing_foreign_reference",
                    total_rows,
                    "Referential integrity rule must include foreign_table and foreign_column.",
                    failed_rows=1,
                )
            )
            continue

        if table_loader is None:
            results.append(
                _build_failure_result(
                    dataset_name,
                    "referential_integrity_check",
                    column,
                    f"{column}_must_exist_in_{foreign_table}.{foreign_column}",
                    total_rows,
                    "No table_loader was provided for referential integrity checks.",
                )
            )
            continue

        try:
            foreign_df = table_loader(foreign_table)
        except Exception as exc:
            logger.exception(
                "Could not load foreign table %s for %s.%s.",
                foreign_table,
                dataset_name,
                column,
            )
            results.append(
                _build_failure_result(
                    dataset_name,
                    "referential_integrity_check",
                    column,
                    f"foreign_table_missing:{foreign_table}",
                    total_rows,
                    f"Could not load foreign table '{foreign_table}': {exc}",
                )
            )
            continue

        if foreign_column not in foreign_df.columns:
            results.append(
                _build_failure_result(
                    dataset_name,
                    "referential_integrity_check",
                    column,
                    f"foreign_column_missing:{foreign_column}",
                    total_rows,
                    f"Foreign column '{foreign_column}' is missing from table '{foreign_table}'.",
                )
            )
            continue

        valid_values = set(foreign_df[foreign_column].dropna())
        failed_df = df[df[column].notnull() & ~df[column].isin(valid_values)]
        failed_rows = len(failed_df)
        details = make_issue_details(
            failed_df,
            dataset_name,
            "referential_integrity_check",
            column,
            f"{column} must exist in {foreign_table}.{foreign_column}.",
        )

        results.append(
            build_result(
                dataset_name,
                "referential_integrity_check",
                column,
                f"{column}_must_exist_in_{foreign_table}.{foreign_column}",
                total_rows,
                failed_rows,
                details=details,
            )
        )

    return results


def _email_domain_rule_config(email_domain_rules):
    """Normalize custom_rules.email_domains into a column and domains list."""

    if not isinstance(email_domain_rules, dict):
        raise ValueError("custom_rules.email_domains must be a mapping.")

    column = email_domain_rules.get("column", "email")
    allowed_domains = [
        str(domain).lower()
        for domain in email_domain_rules.get("allowed_domains", [])
    ]

    return column, allowed_domains


def check_custom_rules(df, dataset_name, custom_rules):
    """Run supported custom rules, currently email domain validation."""

    if not isinstance(custom_rules, dict):
        raise ValueError("custom_rules must be a mapping.")

    results = []
    total_rows = _total_rows(df)

    if "email_domains" not in custom_rules:
        return results

    column, allowed_domains = _email_domain_rule_config(custom_rules["email_domains"])

    if column not in df.columns:
        results.append(
            _column_missing_result(
                df,
                dataset_name,
                "custom_email_domain_check",
                column,
                "email_column_missing",
            )
        )
        return results

    if not allowed_domains:
        results.append(
            _build_failure_result(
                dataset_name,
                "custom_email_domain_check",
                column,
                "missing_allowed_domains",
                total_rows,
                "Email domain rule must include at least one allowed domain.",
                failed_rows=1,
            )
        )
        return results

    non_null_df = _non_null_values(df, column).copy()
    valid_email_mask = (
        non_null_df[column]
        .astype(str)
        .str.match(FORMAT_PATTERNS["email"], na=False)
    )
    valid_email_df = non_null_df[valid_email_mask].copy()

    valid_email_df["email_domain"] = (
        valid_email_df[column]
        .astype(str)
        .str.split("@")
        .str[-1]
        .str.lower()
    )

    failed_df = valid_email_df[
        ~valid_email_df["email_domain"].isin(allowed_domains)
    ].drop(columns=["email_domain"])

    failed_rows = len(failed_df)
    details = make_issue_details(
        failed_df,
        dataset_name,
        "custom_email_domain_check",
        column,
        f"{column} domain must be one of: {allowed_domains}.",
    )

    results.append(
        build_result(
            dataset_name,
            "custom_email_domain_check",
            column,
            f"allowed_domains:{allowed_domains}",
            total_rows,
            failed_rows,
            details=details,
        )
    )

    return results


def _execute_rule_group(
    handler: Callable[..., list[dict[str, Any]]],
    dataset_name,
    check_type,
    rule_name,
    total_rows,
    *args,
):
    """Run one rule group and return a FAIL result if it raises."""

    try:
        return handler(*args)
    except Exception as exc:
        logger.exception(
            "Rule group %s failed for dataset %s.",
            rule_name,
            dataset_name,
        )
        return [
            _build_failure_result(
                dataset_name=dataset_name,
                check_type=check_type,
                column_name=None,
                rule=rule_name,
                total_rows=total_rows,
                reason=f"Rule group '{rule_name}' failed: {exc}",
            )
        ]


def run_rules_for_dataset(df, dataset_name, dataset_rules, table_loader=None):
    """Run all configured rules for one dataset and return result dictionaries.

    A single broken rule group is converted into a FAIL result so the rest of
    the run can continue.
    """

    if not isinstance(df, pd.DataFrame):
        return [
            _build_failure_result(
                dataset_name=dataset_name,
                check_type="rule_execution_error",
                column_name=None,
                rule="invalid_dataset",
                total_rows=0,
                reason="run_rules_for_dataset expected a pandas DataFrame.",
            )
        ]

    if not isinstance(dataset_rules, dict):
        return [
            _build_failure_result(
                dataset_name=dataset_name,
                check_type="rule_execution_error",
                column_name=None,
                rule="invalid_rules",
                total_rows=_total_rows(df),
                reason="Dataset rules must be a mapping.",
            )
        ]

    results = []
    total_rows = _total_rows(df)

    rule_handlers = [
        (
            "required_columns",
            "required_column_check",
            check_required_columns,
            (df, dataset_name, dataset_rules.get("required_columns")),
        ),
        (
            "not_null_columns",
            "not_null_check",
            check_not_null_columns,
            (df, dataset_name, dataset_rules.get("not_null_columns")),
        ),
        (
            "unique_columns",
            "unique_check",
            check_unique_columns,
            (df, dataset_name, dataset_rules.get("unique_columns")),
        ),
        (
            "format_checks",
            "format_check",
            check_format_rules,
            (df, dataset_name, dataset_rules.get("format_checks")),
        ),
        (
            "range_checks",
            "range_check",
            check_range_rules,
            (df, dataset_name, dataset_rules.get("range_checks")),
        ),
        (
            "categorical_checks",
            "categorical_check",
            check_categorical_rules,
            (df, dataset_name, dataset_rules.get("categorical_checks")),
        ),
        (
            "freshness",
            "freshness_check",
            check_freshness_rules,
            (df, dataset_name, dataset_rules.get("freshness")),
        ),
        (
            "referential_integrity",
            "referential_integrity_check",
            check_referential_integrity,
            (df, dataset_name, dataset_rules.get("referential_integrity"), table_loader),
        ),
        (
            "custom_rules",
            "custom_email_domain_check",
            check_custom_rules,
            (df, dataset_name, dataset_rules.get("custom_rules")),
        ),
    ]

    for rule_name, check_type, handler, args in rule_handlers:
        if rule_name not in dataset_rules:
            continue

        results.extend(
            _execute_rule_group(
                handler,
                dataset_name,
                check_type,
                rule_name,
                total_rows,
                *args,
            )
        )

    return results
