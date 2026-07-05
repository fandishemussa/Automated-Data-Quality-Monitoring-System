"""Select the configured source database connector."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import pandas as pd
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")

SUPPORTED_SOURCE_TYPES = {"postgres", "redshift", "snowflake", "bigquery"}


@dataclass(frozen=True)
class SourceFunctions:
    """Callable source connector functions used by the monitoring run."""

    load_table: Callable[[str], pd.DataFrame]
    get_table_names: Callable[[], list[str]]
    get_table_description: Callable[[str], pd.DataFrame]


def get_source_type(source_type: str | None = None) -> str:
    """Return the normalized configured source database type."""

    configured_type = (
        source_type
        or os.getenv("SOURCE_DB_TYPE")
        or os.getenv("DATA_SOURCE_TYPE")
        or "postgres"
    )
    normalized = configured_type.strip().lower()

    if normalized not in SUPPORTED_SOURCE_TYPES:
        supported = ", ".join(sorted(SUPPORTED_SOURCE_TYPES))
        raise ValueError(
            f"Unsupported source database type: {configured_type!r}. "
            f"Supported values: {supported}."
        )

    return normalized


def get_source_module_name(source_type: str | None = None) -> str:
    """Return the module name used for the configured source type."""

    normalized = get_source_type(source_type)
    return {
        "postgres": "data_sources.postgres_connector",
        "redshift": "data_sources.redshift_connector",
        "snowflake": "data_sources.snowflake_connector",
        "bigquery": "data_sources.bigquery_connector",
    }[normalized]


def get_source_functions(source_type: str | None = None) -> SourceFunctions:
    """Return source connector functions for the configured source type."""

    normalized = get_source_type(source_type)

    if normalized == "postgres":
        from data_sources.postgres_connector import (
            get_table_description,
            get_table_names,
            load_table,
        )

        return SourceFunctions(
            load_table=load_table,
            get_table_names=get_table_names,
            get_table_description=get_table_description,
        )

    if normalized == "redshift":
        from data_sources.redshift_connector import (
            get_redshift_table_description,
            get_redshift_table_names,
            load_redshift_table,
        )

        return SourceFunctions(
            load_table=load_redshift_table,
            get_table_names=get_redshift_table_names,
            get_table_description=get_redshift_table_description,
        )

    if normalized == "snowflake":
        from data_sources.snowflake_connector import (
            get_snowflake_table_description,
            get_snowflake_table_names,
            load_snowflake_table,
        )

        return SourceFunctions(
            load_table=load_snowflake_table,
            get_table_names=get_snowflake_table_names,
            get_table_description=get_snowflake_table_description,
        )

    if normalized == "bigquery":
        from data_sources.bigquery_connector import (
            get_bigquery_table_description,
            get_bigquery_table_names,
            load_bigquery_table,
        )

        return SourceFunctions(
            load_table=load_bigquery_table,
            get_table_names=get_bigquery_table_names,
            get_table_description=get_bigquery_table_description,
        )

    raise ValueError(f"Unsupported source database type: {normalized!r}.")
