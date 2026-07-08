"""Snowflake source connector scaffold with clear optional dependency guidance."""

from __future__ import annotations

import pandas as pd


def create_snowflake_client():
    """Create a Snowflake client when optional dependencies are installed."""

    try:
        import snowflake.connector  # noqa: F401
    except ImportError as exc:
        raise ImportError(
            "Snowflake source support requires optional dependencies. "
            "Install them with: pip install -r requirements-snowflake.txt"
        ) from exc

    raise NotImplementedError(
        "Snowflake source extraction is scaffolded but not fully configured yet. "
        "Set SNOWFLAKE_ACCOUNT, SNOWFLAKE_USER, SNOWFLAKE_PASSWORD, "
        "SNOWFLAKE_WAREHOUSE, SNOWFLAKE_DATABASE, and SNOWFLAKE_SCHEMA before "
        "completing this connector."
    )


def load_snowflake_table(table_name):
    """Load a Snowflake table."""

    create_snowflake_client()


def get_snowflake_table_names():
    """Return Snowflake table names."""

    create_snowflake_client()


def get_snowflake_table_description(table_name):
    """Return Snowflake table metadata."""

    create_snowflake_client()


class SnowflakeConnector:
    """Canonical Snowflake source connector placeholder."""

    def load_table(self, table_name: str) -> pd.DataFrame:
        """Load a Snowflake table."""

        return load_snowflake_table(table_name)

    def get_table_names(self) -> list[str]:
        """Return Snowflake table names."""

        return get_snowflake_table_names()

    def get_table_description(self, table_name: str) -> pd.DataFrame:
        """Return Snowflake table metadata."""

        return get_snowflake_table_description(table_name)

    def test_connection(self) -> bool:
        """Return whether Snowflake dependencies/configuration are available."""

        create_snowflake_client()
        return True
