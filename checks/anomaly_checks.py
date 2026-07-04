"""Statistical anomaly and drift checks for numeric dataset columns."""

import pandas as pd
from sqlalchemy import text

from checks.rule_engine import build_result, make_issue_details, make_message_detail
from data_sources.postgres_connector import create_postgres_engine
from utils.logger import get_logger


logger = get_logger(__name__)

DEFAULT_Z_SCORE_THRESHOLD = 3
DEFAULT_MEAN_DRIFT_THRESHOLD_PERCENT = 20


def _numeric_columns(df):
    """Return numeric columns, excluding booleans."""

    return [
        column
        for column in df.select_dtypes(include=["number"]).columns
        if not pd.api.types.is_bool_dtype(df[column])
    ]


def _enabled(config):
    """Return True when a global rule config is enabled."""

    return bool(config.get("enabled", False)) if isinstance(config, dict) else False


def _z_score_enabled(anomaly_config):
    """Return True when z-score anomaly detection should run."""

    methods = anomaly_config.get("methods", ["z_score"])
    return "z_score" in methods


def _load_previous_profile_means(dataset_name):
    """Load latest historical profile means for one dataset.

    Missing profile history is expected on first runs, so database errors are
    logged and converted to an empty dictionary.
    """

    query = text("""
        SELECT column_name, mean
        FROM data_profile_results
        WHERE dataset_name = :dataset_name
          AND mean IS NOT NULL
          AND run_id = (
              SELECT MAX(run_id)
              FROM data_profile_results
              WHERE dataset_name = :dataset_name
                AND mean IS NOT NULL
          )
    """)

    try:
        engine = create_postgres_engine()
        profile_df = pd.read_sql(
            query,
            engine,
            params={"dataset_name": dataset_name},
        )
    except Exception:
        logger.info(
            "No historical profile means available for dataset %s.",
            dataset_name,
        )
        return {}

    return {
        row["column_name"]: float(row["mean"])
        for _, row in profile_df.iterrows()
        if pd.notna(row["mean"])
    }


def _mean_change_percent(current_mean, previous_mean):
    """Calculate absolute percentage change between two means."""

    if previous_mean == 0:
        return 0 if current_mean == 0 else 100

    return abs((current_mean - previous_mean) / previous_mean) * 100


def check_z_score_anomalies(
    df,
    dataset_name,
    threshold=DEFAULT_Z_SCORE_THRESHOLD,
):
    """Detect numeric values with absolute z-score greater than threshold."""

    results = []
    total_rows = len(df)

    for column in _numeric_columns(df):
        numeric_values = pd.to_numeric(df[column], errors="coerce")
        valid_values = numeric_values.dropna()

        if len(valid_values) < 2:
            results.append(
                build_result(
                    dataset_name=dataset_name,
                    check_type="z_score_anomaly_check",
                    column_name=column,
                    rule=f"abs_z_score_gt:{threshold}",
                    total_rows=total_rows,
                    failed_rows=0,
                    status="SKIPPED",
                    details=make_message_detail(
                        dataset_name,
                        "z_score_anomaly_check",
                        column,
                        "Not enough numeric values for z-score anomaly detection.",
                    ),
                )
            )
            continue

        mean = valid_values.mean()
        std = valid_values.std()

        if pd.isna(std) or std == 0:
            results.append(
                build_result(
                    dataset_name=dataset_name,
                    check_type="z_score_anomaly_check",
                    column_name=column,
                    rule=f"abs_z_score_gt:{threshold}",
                    total_rows=total_rows,
                    failed_rows=0,
                    status="SKIPPED",
                    details=make_message_detail(
                        dataset_name,
                        "z_score_anomaly_check",
                        column,
                        "Standard deviation is zero, so z-score detection was skipped.",
                    ),
                )
            )
            continue

        z_scores = (numeric_values - mean) / std
        failed_mask = z_scores.abs() > threshold
        failed_df = df[failed_mask].copy()

        if not failed_df.empty:
            failed_df["z_score"] = z_scores[failed_mask].round(4)

        failed_rows = len(failed_df)
        details = make_issue_details(
            failed_df,
            dataset_name,
            "z_score_anomaly_check",
            column,
            f"{column} has absolute z-score greater than {threshold}.",
        )

        results.append(
            build_result(
                dataset_name=dataset_name,
                check_type="z_score_anomaly_check",
                column_name=column,
                rule=f"abs_z_score_gt:{threshold}",
                total_rows=total_rows,
                failed_rows=failed_rows,
                details=details,
            )
        )

    return results


def check_mean_drift(
    df,
    dataset_name,
    threshold_percent=DEFAULT_MEAN_DRIFT_THRESHOLD_PERCENT,
    previous_means=None,
):
    """Compare current numeric means with latest historical profile means."""

    previous_means = previous_means or _load_previous_profile_means(dataset_name)
    results = []
    total_rows = len(df)

    for column in _numeric_columns(df):
        numeric_values = pd.to_numeric(df[column], errors="coerce").dropna()

        if numeric_values.empty:
            results.append(
                build_result(
                    dataset_name=dataset_name,
                    check_type="data_drift_check",
                    column_name=column,
                    rule=f"mean_change_percent_gt:{threshold_percent}",
                    total_rows=total_rows,
                    failed_rows=0,
                    status="SKIPPED",
                    details=make_message_detail(
                        dataset_name,
                        "data_drift_check",
                        column,
                        "No numeric values available for drift detection.",
                    ),
                )
            )
            continue

        current_mean = float(numeric_values.mean())
        previous_mean = previous_means.get(column)

        if previous_mean is None:
            results.append(
                build_result(
                    dataset_name=dataset_name,
                    check_type="data_drift_check",
                    column_name=column,
                    rule=f"mean_change_percent_gt:{threshold_percent}",
                    total_rows=total_rows,
                    failed_rows=0,
                    status="SKIPPED",
                    details=make_message_detail(
                        dataset_name,
                        "data_drift_check",
                        column,
                        "No historical mean found for this column.",
                    ),
                )
            )
            continue

        change_percent = _mean_change_percent(current_mean, previous_mean)
        has_drift = change_percent > threshold_percent
        reason = (
            f"Current mean {current_mean:.4f} changed by {change_percent:.2f}% "
            f"from previous mean {previous_mean:.4f}; threshold is "
            f"{threshold_percent}%."
        )

        results.append(
            build_result(
                dataset_name=dataset_name,
                check_type="data_drift_check",
                column_name=column,
                rule=f"mean_change_percent_gt:{threshold_percent}",
                total_rows=total_rows,
                failed_rows=total_rows if has_drift else 0,
                status="FAIL" if has_drift else "PASS",
                details=(
                    make_message_detail(
                        dataset_name,
                        "data_drift_check",
                        column,
                        reason,
                    )
                    if has_drift
                    else []
                ),
            )
        )

    return results


def run_statistical_checks(df, dataset_name, global_rules):
    """Run enabled anomaly and drift checks for a dataset."""

    if not isinstance(df, pd.DataFrame):
        return [
            build_result(
                dataset_name=dataset_name,
                check_type="statistical_check_error",
                column_name=None,
                rule="invalid_dataset",
                total_rows=0,
                failed_rows=1,
                status="FAIL",
                details=make_message_detail(
                    dataset_name,
                    "statistical_check_error",
                    None,
                    "Statistical checks expected a pandas DataFrame.",
                ),
            )
        ]

    if not isinstance(global_rules, dict):
        global_rules = {}

    results = []
    anomaly_config = global_rules.get("anomaly_detection", {})
    drift_config = global_rules.get("data_drift_detection", {})

    try:
        if _enabled(anomaly_config) and _z_score_enabled(anomaly_config):
            z_score_threshold = anomaly_config.get(
                "z_score_threshold",
                DEFAULT_Z_SCORE_THRESHOLD,
            )
            results.extend(
                check_z_score_anomalies(
                    df,
                    dataset_name,
                    threshold=float(z_score_threshold),
                )
            )

        if _enabled(drift_config):
            threshold_percent = drift_config.get(
                "mean_change_threshold_percent",
                DEFAULT_MEAN_DRIFT_THRESHOLD_PERCENT,
            )
            results.extend(
                check_mean_drift(
                    df,
                    dataset_name,
                    threshold_percent=float(threshold_percent),
                )
            )
    except Exception as exc:
        logger.exception("Statistical checks failed for dataset %s.", dataset_name)
        results.append(
            build_result(
                dataset_name=dataset_name,
                check_type="statistical_check_error",
                column_name=None,
                rule="anomaly_or_drift_checks",
                total_rows=len(df),
                failed_rows=len(df) if len(df) > 0 else 1,
                status="FAIL",
                details=make_message_detail(
                    dataset_name,
                    "statistical_check_error",
                    None,
                    f"Statistical checks failed: {exc}",
                ),
            )
        )

    return results
