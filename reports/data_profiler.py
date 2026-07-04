"""Column-level data profiling for monitored datasets."""

from datetime import date, datetime
from typing import Any

import pandas as pd
from sqlalchemy import text

from data_sources.postgres_connector import create_postgres_engine
from utils.logger import get_logger


logger = get_logger(__name__)


CREATE_PROFILE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS data_profile_results (
    id SERIAL PRIMARY KEY,
    run_id INT,
    dataset_name VARCHAR(100),
    column_name VARCHAR(100),
    data_type VARCHAR(100),
    total_rows INT,
    null_count INT,
    null_rate FLOAT,
    unique_count INT,
    duplicate_count INT,
    min_value TEXT,
    max_value TEXT,
    mean FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
"""


INSERT_PROFILE_RESULT_SQL = """
INSERT INTO data_profile_results (
    run_id,
    dataset_name,
    column_name,
    data_type,
    total_rows,
    null_count,
    null_rate,
    unique_count,
    duplicate_count,
    min_value,
    max_value,
    mean
)
VALUES (
    :run_id,
    :dataset_name,
    :column_name,
    :data_type,
    :total_rows,
    :null_count,
    :null_rate,
    :unique_count,
    :duplicate_count,
    :min_value,
    :max_value,
    :mean
)
"""


def _safe_text(value: Any):
    """Return a database-friendly text value, preserving SQL NULL when empty."""

    if value is None:
        return None

    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass

    return str(value)


def _safe_float(value: Any):
    """Return a database-friendly float value or None."""

    if value is None:
        return None

    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        return None

    return float(value)


def _profile_numeric_column(series):
    """Calculate numeric min, max, and mean for a column."""

    numeric_values = pd.to_numeric(series, errors="coerce")

    if numeric_values.dropna().empty:
        return None, None, None

    return (
        _safe_text(numeric_values.min()),
        _safe_text(numeric_values.max()),
        _safe_float(numeric_values.mean()),
    )


def _profile_datetime_column(series):
    """Calculate datetime min and max for a column."""

    datetime_values = pd.to_datetime(series, errors="coerce")

    if datetime_values.dropna().empty:
        return None, None

    return (
        _safe_text(datetime_values.min()),
        _safe_text(datetime_values.max()),
    )


def _is_date_like_column(series):
    """Return True for pandas or Python date/datetime columns."""

    if pd.api.types.is_datetime64_any_dtype(series):
        return True

    non_null_values = series.dropna()

    if non_null_values.empty:
        return False

    return non_null_values.map(lambda value: isinstance(value, (date, datetime))).all()


def _duplicate_count(series):
    """Calculate duplicate count when pandas can compare the values safely."""

    try:
        return int(series.duplicated().sum())
    except TypeError:
        logger.debug(
            "Skipping duplicate count for column with unhashable values: %s",
            series.name,
        )
        return None


def profile_dataframe(df, dataset_name):
    """Return column-level profiling records for a DataFrame.

    Each returned dictionary is ready to be inserted into
    `data_profile_results` after a `run_id` is added.
    """

    if not isinstance(df, pd.DataFrame):
        raise TypeError("profile_dataframe expects a pandas DataFrame.")

    total_rows = len(df)
    profiles = []

    for column_name in df.columns:
        series = df[column_name]
        null_count = int(series.isnull().sum())
        null_rate = round(float(null_count / total_rows), 4) if total_rows > 0 else 0
        unique_count = int(series.nunique(dropna=True))
        duplicate_count = _duplicate_count(series)
        min_value = None
        max_value = None
        mean_value = None

        if (
            pd.api.types.is_numeric_dtype(series)
            and not pd.api.types.is_bool_dtype(series)
        ):
            min_value, max_value, mean_value = _profile_numeric_column(series)
        elif _is_date_like_column(series):
            min_value, max_value = _profile_datetime_column(series)

        profiles.append({
            "dataset_name": dataset_name,
            "column_name": column_name,
            "data_type": str(series.dtype),
            "total_rows": int(total_rows),
            "null_count": null_count,
            "null_rate": null_rate,
            "unique_count": unique_count,
            "duplicate_count": duplicate_count,
            "min_value": min_value,
            "max_value": max_value,
            "mean": mean_value,
        })

    return profiles


def ensure_profile_table_exists(engine=None):
    """Create the profiling results table if it does not already exist."""

    engine = engine or create_postgres_engine()

    with engine.begin() as connection:
        connection.execute(text(CREATE_PROFILE_TABLE_SQL))


def save_profile_results_to_postgres(run_id, profile_results):
    """Save profile result dictionaries for a data quality run."""

    if not profile_results:
        logger.info("No data profile results to save for run %s.", run_id)
        return 0

    engine = create_postgres_engine()
    ensure_profile_table_exists(engine)

    rows = [
        {
            "run_id": run_id,
            "dataset_name": result.get("dataset_name"),
            "column_name": result.get("column_name"),
            "data_type": result.get("data_type"),
            "total_rows": int(result.get("total_rows", 0)),
            "null_count": int(result.get("null_count", 0)),
            "null_rate": float(result.get("null_rate", 0)),
            "unique_count": int(result.get("unique_count", 0)),
            "duplicate_count": result.get("duplicate_count"),
            "min_value": result.get("min_value"),
            "max_value": result.get("max_value"),
            "mean": result.get("mean"),
        }
        for result in profile_results
    ]

    with engine.begin() as connection:
        connection.execute(text(INSERT_PROFILE_RESULT_SQL), rows)

    logger.info("Saved %s data profile result(s) for run %s.", len(rows), run_id)
    return len(rows)


def profile_and_save_datasets(run_id, datasets):
    """Profile multiple loaded datasets and save the combined results."""

    profile_results = []

    for dataset_name, df in datasets.items():
        try:
            dataset_profiles = profile_dataframe(df, dataset_name)
            profile_results.extend(dataset_profiles)
            logger.info(
                "Profiled %s column(s) for dataset %s.",
                len(dataset_profiles),
                dataset_name,
            )
        except Exception as exc:
            logger.exception("Could not profile dataset %s.", dataset_name)
            profile_results.append({
                "dataset_name": dataset_name,
                "column_name": "__profiling_error__",
                "data_type": "ERROR",
                "total_rows": len(df) if isinstance(df, pd.DataFrame) else 0,
                "null_count": 0,
                "null_rate": 0,
                "unique_count": 0,
                "duplicate_count": 0,
                "min_value": str(exc),
                "max_value": None,
                "mean": None,
                "error": str(exc),
            })

    return save_profile_results_to_postgres(run_id, profile_results)
