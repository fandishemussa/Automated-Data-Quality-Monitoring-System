"""Select the configured source database connector."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import pandas as pd
from dotenv import load_dotenv

from data_sources.base_connector import BaseConnector


PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")

SUPPORTED_SOURCE_TYPES = {"postgres", "redshift", "snowflake", "bigquery", "mongodb"}


@dataclass(frozen=True)
class SourceFunctions:
    """Callable source connector functions used by the monitoring run."""

    load_table: Callable[[str], pd.DataFrame]
    get_table_names: Callable[[], list[str]]
    get_table_description: Callable[[str], pd.DataFrame]
    test_connection: Callable[[], bool]


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
        "mongodb": "data_sources.mongodb_connector",
    }[normalized]


def get_source_connector(source_type: str | None = None) -> BaseConnector:
    """Return the canonical connector object for the configured source type."""

    normalized = get_source_type(source_type)

    if normalized == "postgres":
        from data_sources.postgres_connector import PostgresConnector

        return PostgresConnector()

    if normalized == "redshift":
        from data_sources.redshift_connector import RedshiftConnector

        return RedshiftConnector()

    if normalized == "snowflake":
        from data_sources.snowflake_connector import SnowflakeConnector

        return SnowflakeConnector()

    if normalized == "bigquery":
        from data_sources.bigquery_connector import BigQueryConnector

        return BigQueryConnector()

    if normalized == "mongodb":
        from data_sources.mongodb_connector import MongoDBConnector

        return MongoDBConnector()

    raise ValueError(f"Unsupported source database type: {normalized!r}.")


def get_source_functions(source_type: str | None = None) -> SourceFunctions:
    """Return source connector methods for backward-compatible callers."""

    connector = get_source_connector(source_type)
    return SourceFunctions(
        load_table=connector.load_table,
        get_table_names=connector.get_table_names,
        get_table_description=connector.get_table_description,
        test_connection=connector.test_connection,
    )
