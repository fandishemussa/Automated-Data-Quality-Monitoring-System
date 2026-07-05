"""Advanced data drift detection using historical profiling baselines."""

from __future__ import annotations

import json
import math
from typing import Any

import pandas as pd
from sqlalchemy import text

from checks.rule_engine import build_result, make_message_detail
from data_sources.postgres_connector import create_postgres_engine
from utils.logger import get_logger


logger = get_logger(__name__)

DEFAULT_BASELINE_RUNS = 3
DEFAULT_MEAN_CHANGE_THRESHOLD_PERCENT = 25
DEFAULT_STD_CHANGE_THRESHOLD_PERCENT = 30
DEFAULT_PSI_THRESHOLD = 0.2
DEFAULT_CHI_SQUARE_P_VALUE_THRESHOLD = 0.05
PSI_EPSILON = 0.000001


def _enabled(config: dict[str, Any]) -> bool:
    """Return True when drift detection is enabled."""

    return bool(config.get("enabled", False)) if isinstance(config, dict) else False


def _numeric_columns(df: pd.DataFrame) -> list[str]:
    """Return numeric columns, excluding booleans."""

    return [
        column
        for column in df.select_dtypes(include=["number"]).columns
        if not pd.api.types.is_bool_dtype(df[column])
    ]


def _categorical_columns(df: pd.DataFrame) -> list[str]:
    """Return categorical-style columns suitable for distribution checks."""

    columns = []

    for column in df.columns:
        series = df[column]
        if pd.api.types.is_bool_dtype(series):
            columns.append(column)
        elif (
            pd.api.types.is_object_dtype(series)
            or isinstance(series.dtype, pd.CategoricalDtype)
        ):
            columns.append(column)

    return columns


def percentage_change(current_value: float, baseline_value: float) -> float:
    """Calculate absolute percentage change from a baseline value."""

    if baseline_value == 0:
        return 0 if current_value == 0 else 100

    return abs((current_value - baseline_value) / baseline_value) * 100


def _normalize_distribution(distribution: dict[str, float]) -> dict[str, float]:
    """Normalize counts or proportions into proportions."""

    cleaned = {
        str(key): max(float(value), 0.0)
        for key, value in distribution.items()
        if value is not None
    }
    total = sum(cleaned.values())

    if total <= 0:
        return {key: 0.0 for key in cleaned}

    return {
        key: value / total
        for key, value in cleaned.items()
    }


def calculate_psi(
    expected_distribution: dict[str, float],
    actual_distribution: dict[str, float],
    epsilon: float = PSI_EPSILON,
) -> float:
    """Calculate Population Stability Index for aligned distributions.

    `expected_distribution` is the historical baseline and
    `actual_distribution` is the current run. Inputs can be counts or already
    normalized proportions.
    """

    expected = _normalize_distribution(expected_distribution)
    actual = _normalize_distribution(actual_distribution)
    keys = sorted(set(expected) | set(actual))

    if not keys:
        return 0.0

    psi = 0.0

    for key in keys:
        expected_value = max(expected.get(key, 0.0), epsilon)
        actual_value = max(actual.get(key, 0.0), epsilon)
        psi += (actual_value - expected_value) * math.log(actual_value / expected_value)

    return round(float(psi), 6)


def _normal_cdf(value: float, mean: float, std_dev: float) -> float:
    """Return normal CDF without requiring scipy."""

    if std_dev <= 0:
        return 0.0 if value < mean else 1.0

    z_score = (value - mean) / (std_dev * math.sqrt(2))
    return 0.5 * (1 + math.erf(z_score))


def _normal_distribution_across_baseline_bins(
    baseline_mean: float,
    baseline_std: float,
    current_mean: float,
    current_std: float,
) -> tuple[dict[str, float], dict[str, float]]:
    """Build expected/current normal distributions across baseline sigma bins."""

    labels = [
        "lt_-2_sigma",
        "-2_to_-1_sigma",
        "-1_to_0_sigma",
        "0_to_1_sigma",
        "1_to_2_sigma",
        "gt_2_sigma",
    ]
    z_boundaries = [-math.inf, -2, -1, 0, 1, 2, math.inf]
    raw_boundaries = [
        (
            baseline_mean + z_value * baseline_std
            if math.isfinite(z_value)
            else z_value
        )
        for z_value in z_boundaries
    ]

    expected = {}
    actual = {}

    for index, label in enumerate(labels):
        lower_z = z_boundaries[index]
        upper_z = z_boundaries[index + 1]
        lower_raw = raw_boundaries[index]
        upper_raw = raw_boundaries[index + 1]

        expected_lower = 0.0 if lower_z == -math.inf else _normal_cdf(lower_z, 0, 1)
        expected_upper = 1.0 if upper_z == math.inf else _normal_cdf(upper_z, 0, 1)
        actual_lower = 0.0 if lower_raw == -math.inf else _normal_cdf(lower_raw, current_mean, current_std)
        actual_upper = 1.0 if upper_raw == math.inf else _normal_cdf(upper_raw, current_mean, current_std)

        expected[label] = max(expected_upper - expected_lower, 0.0)
        actual[label] = max(actual_upper - actual_lower, 0.0)

    return expected, actual


def _load_historical_profiles(
    dataset_name: str,
    baseline_runs: int,
    current_run_id: int | None = None,
) -> pd.DataFrame:
    """Load historical profile rows used as drift baselines."""

    query = text(
        """
        SELECT *
        FROM data_profile_results
        WHERE dataset_name = :dataset_name
        ORDER BY run_id DESC, id DESC
        """
    )

    try:
        engine = create_postgres_engine()
        history_df = pd.read_sql(query, engine, params={"dataset_name": dataset_name})
    except Exception:
        logger.info("No historical profile baseline found for dataset %s.", dataset_name)
        return pd.DataFrame()

    if current_run_id is not None and "run_id" in history_df.columns:
        history_df = history_df[history_df["run_id"] < current_run_id]

    if history_df.empty or "run_id" not in history_df.columns:
        return history_df.iloc[0:0].copy()

    baseline_run_ids = (
        history_df["run_id"]
        .dropna()
        .drop_duplicates()
        .head(max(int(baseline_runs), 1))
        .tolist()
    )

    return history_df[history_df["run_id"].isin(baseline_run_ids)].copy()


def _numeric_baseline(
    historical_profiles: pd.DataFrame,
    column: str,
) -> dict[str, float | None]:
    """Return baseline mean/std for one numeric column."""

    if historical_profiles.empty or "column_name" not in historical_profiles.columns:
        return {"mean": None, "std_dev": None}

    column_history = historical_profiles[historical_profiles["column_name"] == column]

    if column_history.empty:
        return {"mean": None, "std_dev": None}

    mean_source = (
        column_history["mean"]
        if "mean" in column_history.columns
        else pd.Series(dtype=float)
    )
    std_source = (
        column_history["std_dev"]
        if "std_dev" in column_history.columns
        else pd.Series(dtype=float)
    )
    mean_values = pd.to_numeric(mean_source, errors="coerce").dropna()
    std_values = pd.to_numeric(std_source, errors="coerce").dropna()

    return {
        "mean": float(mean_values.mean()) if not mean_values.empty else None,
        "std_dev": float(std_values.mean()) if not std_values.empty else None,
    }


def _distribution_from_series(series: pd.Series) -> dict[str, int]:
    """Return a simple count distribution for current categorical values."""

    return (
        series
        .fillna("__NULL__")
        .astype(str)
        .value_counts(dropna=False)
        .to_dict()
    )


def _parse_distribution(raw_distribution: Any) -> dict[str, float]:
    """Parse a JSON distribution stored by the data profiler."""

    if raw_distribution is None or pd.isna(raw_distribution):
        return {}

    if isinstance(raw_distribution, dict):
        return raw_distribution

    try:
        parsed = json.loads(str(raw_distribution))
    except (TypeError, ValueError, json.JSONDecodeError):
        return {}

    if not isinstance(parsed, dict):
        return {}

    return {
        str(key): float(value)
        for key, value in parsed.items()
    }


def _baseline_distribution(
    historical_profiles: pd.DataFrame,
    column: str,
) -> dict[str, float]:
    """Combine stored historical distributions for one categorical column."""

    if (
        historical_profiles.empty
        or "column_name" not in historical_profiles.columns
        or "value_distribution" not in historical_profiles.columns
    ):
        return {}

    column_history = historical_profiles[historical_profiles["column_name"] == column]
    combined: dict[str, float] = {}

    for raw_distribution in column_history["value_distribution"].dropna():
        parsed_distribution = _parse_distribution(raw_distribution)
        for category, count in parsed_distribution.items():
            combined[category] = combined.get(category, 0.0) + float(count)

    return combined


def _drift_detail(
    dataset_name: str,
    column: str,
    method: str,
    current_value: Any,
    baseline_value: Any,
    threshold: Any,
    metric_value: Any,
    reason: str,
    percent_change: float | None = None,
    extra: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Build one column-level issue detail for drift checks."""

    payload = {
        "drift_method": method,
        "current_value": current_value,
        "baseline_value": baseline_value,
        "percent_change": percent_change,
        "threshold": threshold,
        "metric_value": metric_value,
    }

    if extra:
        payload.update(extra)

    return [{
        "dataset_name": dataset_name,
        "check_type": "data_drift_check",
        "column_name": column,
        "row_identifier": "column_level",
        "bad_value": str(current_value),
        "reason": reason,
        "sample_row": json.dumps(payload, sort_keys=True),
    }]


def _skipped_result(
    dataset_name: str,
    column: str,
    rule: str,
    reason: str,
    total_rows: int,
) -> dict[str, Any]:
    """Return a skipped drift result with a friendly reason."""

    return build_result(
        dataset_name=dataset_name,
        check_type="data_drift_check",
        column_name=column,
        rule=rule,
        total_rows=total_rows,
        failed_rows=0,
        status="SKIPPED",
        details=make_message_detail(
            dataset_name,
            "data_drift_check",
            column,
            reason,
        ),
    )


def _metric_result(
    dataset_name: str,
    column: str,
    rule: str,
    method: str,
    current_value: Any,
    baseline_value: Any,
    metric_value: float,
    threshold: float,
    total_rows: int,
    reason: str,
    percent_change: float | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return a PASS/FAIL result for one drift metric."""

    has_drift = metric_value > threshold

    return build_result(
        dataset_name=dataset_name,
        check_type="data_drift_check",
        column_name=column,
        rule=rule,
        total_rows=total_rows,
        failed_rows=total_rows if has_drift else 0,
        status="FAIL" if has_drift else "PASS",
        details=(
            _drift_detail(
                dataset_name=dataset_name,
                column=column,
                method=method,
                current_value=current_value,
                baseline_value=baseline_value,
                threshold=threshold,
                metric_value=metric_value,
                percent_change=percent_change,
                reason=reason,
                extra=extra,
            )
            if has_drift
            else []
        ),
    )


def check_numeric_drift(
    df: pd.DataFrame,
    dataset_name: str,
    historical_profiles: pd.DataFrame,
    drift_config: dict[str, Any],
) -> list[dict[str, Any]]:
    """Run mean, standard deviation, and PSI drift checks for numeric columns."""

    total_rows = len(df)
    results = []
    mean_threshold = float(
        drift_config.get(
            "mean_change_threshold_percent",
            DEFAULT_MEAN_CHANGE_THRESHOLD_PERCENT,
        )
    )
    std_threshold = float(
        drift_config.get(
            "std_change_threshold_percent",
            DEFAULT_STD_CHANGE_THRESHOLD_PERCENT,
        )
    )
    psi_threshold = float(drift_config.get("psi_threshold", DEFAULT_PSI_THRESHOLD))

    for column in _numeric_columns(df):
        current_values = pd.to_numeric(df[column], errors="coerce").dropna()

        if current_values.empty:
            results.append(
                _skipped_result(
                    dataset_name,
                    column,
                    "numeric_drift",
                    "No current numeric values are available for drift detection.",
                    total_rows,
                )
            )
            continue

        current_mean = float(current_values.mean())
        current_std = float(current_values.std()) if len(current_values) > 1 else 0.0
        baseline = _numeric_baseline(historical_profiles, column)
        baseline_mean = baseline["mean"]
        baseline_std = baseline["std_dev"]

        if baseline_mean is None:
            results.append(
                _skipped_result(
                    dataset_name,
                    column,
                    f"mean_change_percent_gt:{mean_threshold}",
                    "No historical mean baseline found for this column.",
                    total_rows,
                )
            )
        else:
            change_percent = percentage_change(current_mean, baseline_mean)
            reason = (
                f"Mean drift detected for {column}: current value {current_mean:.4f}, "
                f"baseline value {baseline_mean:.4f}, percent change "
                f"{change_percent:.2f}%, method mean_percentage_change."
            )
            results.append(
                _metric_result(
                    dataset_name=dataset_name,
                    column=column,
                    rule=f"mean_change_percent_gt:{mean_threshold}",
                    method="mean_percentage_change",
                    current_value=round(current_mean, 6),
                    baseline_value=round(baseline_mean, 6),
                    metric_value=round(change_percent, 6),
                    threshold=mean_threshold,
                    total_rows=total_rows,
                    reason=reason,
                    percent_change=round(change_percent, 6),
                )
            )

        if baseline_std is None:
            results.append(
                _skipped_result(
                    dataset_name,
                    column,
                    f"std_change_percent_gt:{std_threshold}",
                    "No historical standard deviation baseline found for this column.",
                    total_rows,
                )
            )
        else:
            std_change_percent = percentage_change(current_std, baseline_std)
            reason = (
                f"Standard deviation drift detected for {column}: current value "
                f"{current_std:.4f}, baseline value {baseline_std:.4f}, percent "
                f"change {std_change_percent:.2f}%, method std_percentage_change."
            )
            results.append(
                _metric_result(
                    dataset_name=dataset_name,
                    column=column,
                    rule=f"std_change_percent_gt:{std_threshold}",
                    method="std_percentage_change",
                    current_value=round(current_std, 6),
                    baseline_value=round(baseline_std, 6),
                    metric_value=round(std_change_percent, 6),
                    threshold=std_threshold,
                    total_rows=total_rows,
                    reason=reason,
                    percent_change=round(std_change_percent, 6),
                )
            )

        if baseline_mean is None or baseline_std is None or baseline_std <= 0:
            results.append(
                _skipped_result(
                    dataset_name,
                    column,
                    f"psi_gt:{psi_threshold}",
                    "Numeric PSI needs historical mean and non-zero standard deviation baselines.",
                    total_rows,
                )
            )
            continue

        expected_distribution, actual_distribution = _normal_distribution_across_baseline_bins(
            baseline_mean=baseline_mean,
            baseline_std=baseline_std,
            current_mean=current_mean,
            current_std=current_std,
        )
        psi_value = calculate_psi(expected_distribution, actual_distribution)
        reason = (
            f"PSI drift detected for {column}: current PSI {psi_value:.4f}, "
            f"threshold {psi_threshold}, method numeric_psi."
        )
        results.append(
            _metric_result(
                dataset_name=dataset_name,
                column=column,
                rule=f"psi_gt:{psi_threshold}",
                method="numeric_psi",
                current_value=round(psi_value, 6),
                baseline_value="baseline_normal_distribution",
                metric_value=psi_value,
                threshold=psi_threshold,
                total_rows=total_rows,
                reason=reason,
                extra={
                    "expected_distribution": expected_distribution,
                    "actual_distribution": actual_distribution,
                },
            )
        )

    return results


def _chi_square_result(
    dataset_name: str,
    column: str,
    baseline_distribution: dict[str, float],
    current_distribution: dict[str, int],
    total_rows: int,
) -> dict[str, Any] | None:
    """Run a scipy chi-square distribution check when scipy is installed."""

    try:
        from scipy.stats import chisquare
    except ImportError:
        return None

    categories = sorted(set(baseline_distribution) | set(current_distribution))

    if len(categories) < 2:
        return None

    baseline_normalized = _normalize_distribution(baseline_distribution)
    observed = [float(current_distribution.get(category, 0.0)) for category in categories]
    observed_total = sum(observed)

    if observed_total <= 0:
        return None

    expected = [
        max(baseline_normalized.get(category, 0.0) * observed_total, PSI_EPSILON)
        for category in categories
    ]
    expected_total = sum(expected)
    expected = [value * observed_total / expected_total for value in expected]

    statistic, p_value = chisquare(f_obs=observed, f_exp=expected)
    metric_value = 1 - float(p_value)
    threshold = 1 - DEFAULT_CHI_SQUARE_P_VALUE_THRESHOLD
    reason = (
        f"Chi-square distribution drift detected for {column}: p-value "
        f"{float(p_value):.6f}, statistic {float(statistic):.4f}, "
        "method categorical_chi_square."
    )

    return _metric_result(
        dataset_name=dataset_name,
        column=column,
        rule=f"chi_square_p_value_lt:{DEFAULT_CHI_SQUARE_P_VALUE_THRESHOLD}",
        method="categorical_chi_square",
        current_value=round(float(p_value), 6),
        baseline_value="historical_category_distribution",
        metric_value=round(metric_value, 6),
        threshold=threshold,
        total_rows=total_rows,
        reason=reason,
        extra={
            "chi_square_statistic": round(float(statistic), 6),
            "chi_square_p_value": round(float(p_value), 6),
            "baseline_distribution": baseline_distribution,
            "current_distribution": current_distribution,
        },
    )


def check_categorical_drift(
    df: pd.DataFrame,
    dataset_name: str,
    historical_profiles: pd.DataFrame,
    drift_config: dict[str, Any],
) -> list[dict[str, Any]]:
    """Run categorical distribution drift checks."""

    total_rows = len(df)
    results = []
    psi_threshold = float(drift_config.get("psi_threshold", DEFAULT_PSI_THRESHOLD))

    for column in _categorical_columns(df):
        current_distribution = _distribution_from_series(df[column])
        baseline_distribution = _baseline_distribution(historical_profiles, column)

        if not baseline_distribution:
            results.append(
                _skipped_result(
                    dataset_name,
                    column,
                    f"categorical_psi_gt:{psi_threshold}",
                    "No historical category distribution baseline found for this column.",
                    total_rows,
                )
            )
            continue

        psi_value = calculate_psi(baseline_distribution, current_distribution)
        baseline_normalized = _normalize_distribution(baseline_distribution)
        current_normalized = _normalize_distribution(current_distribution)
        categories = sorted(set(baseline_normalized) | set(current_normalized))
        distribution_difference = 0.5 * sum(
            abs(current_normalized.get(category, 0.0) - baseline_normalized.get(category, 0.0))
            for category in categories
        )
        reason = (
            f"Categorical distribution drift detected for {column}: PSI "
            f"{psi_value:.4f}, distribution difference "
            f"{distribution_difference:.4f}, method categorical_distribution_psi."
        )
        results.append(
            _metric_result(
                dataset_name=dataset_name,
                column=column,
                rule=f"categorical_psi_gt:{psi_threshold}",
                method="categorical_distribution_psi",
                current_value=round(psi_value, 6),
                baseline_value="historical_category_distribution",
                metric_value=psi_value,
                threshold=psi_threshold,
                total_rows=total_rows,
                reason=reason,
                extra={
                    "distribution_difference": round(float(distribution_difference), 6),
                    "baseline_distribution": baseline_distribution,
                    "current_distribution": current_distribution,
                },
            )
        )

        chi_square_result = _chi_square_result(
            dataset_name=dataset_name,
            column=column,
            baseline_distribution=baseline_distribution,
            current_distribution=current_distribution,
            total_rows=total_rows,
        )

        if chi_square_result is not None:
            results.append(chi_square_result)

    return results


def run_advanced_drift_checks(
    df: pd.DataFrame,
    dataset_name: str,
    drift_config: dict[str, Any],
    current_run_id: int | None = None,
    historical_profiles: pd.DataFrame | None = None,
) -> list[dict[str, Any]]:
    """Run advanced drift checks for one dataset."""

    if not isinstance(df, pd.DataFrame):
        return [
            build_result(
                dataset_name=dataset_name,
                check_type="data_drift_check",
                column_name=None,
                rule="invalid_dataset",
                total_rows=0,
                failed_rows=1,
                status="FAIL",
                details=make_message_detail(
                    dataset_name,
                    "data_drift_check",
                    None,
                    "Drift checks expected a pandas DataFrame.",
                ),
            )
        ]

    if not _enabled(drift_config):
        return []

    baseline_runs = int(drift_config.get("baseline_runs", DEFAULT_BASELINE_RUNS))
    historical_profiles = (
        historical_profiles
        if historical_profiles is not None
        else _load_historical_profiles(dataset_name, baseline_runs, current_run_id)
    )

    if historical_profiles.empty:
        return [
            build_result(
                dataset_name=dataset_name,
                check_type="data_drift_check",
                column_name=None,
                rule=f"baseline_runs:{baseline_runs}",
                total_rows=len(df),
                failed_rows=0,
                status="SKIPPED",
                details=make_message_detail(
                    dataset_name,
                    "data_drift_check",
                    None,
                    "No historical profile baseline is available for drift detection.",
                ),
            )
        ]

    results = []
    results.extend(check_numeric_drift(df, dataset_name, historical_profiles, drift_config))
    results.extend(check_categorical_drift(df, dataset_name, historical_profiles, drift_config))

    return results


def run_advanced_drift_checks_for_datasets(
    datasets: dict[str, pd.DataFrame],
    global_rules: dict[str, Any],
    current_run_id: int | None = None,
) -> list[dict[str, Any]]:
    """Run advanced drift checks for all loaded datasets."""

    drift_config = global_rules.get("data_drift_detection", {})

    if not _enabled(drift_config):
        return []

    results = []

    for dataset_name, df in datasets.items():
        try:
            dataset_results = run_advanced_drift_checks(
                df=df,
                dataset_name=dataset_name,
                drift_config=drift_config,
                current_run_id=current_run_id,
            )
            results.extend(dataset_results)
            logger.info(
                "Completed %s advanced drift check result(s) for %s.",
                len(dataset_results),
                dataset_name,
            )
        except Exception as exc:
            logger.exception("Advanced drift checks failed for dataset %s.", dataset_name)
            results.append(
                build_result(
                    dataset_name=dataset_name,
                    check_type="data_drift_check",
                    column_name=None,
                    rule="advanced_drift_checks",
                    total_rows=len(df) if isinstance(df, pd.DataFrame) else 0,
                    failed_rows=len(df) if isinstance(df, pd.DataFrame) and len(df) > 0 else 1,
                    status="FAIL",
                    details=make_message_detail(
                        dataset_name,
                        "data_drift_check",
                        None,
                        f"Advanced drift checks failed: {exc}",
                    ),
                )
            )

    return results
