"""BigQuery source connector scaffold with clear optional dependency guidance."""

from __future__ import annotations

import pandas as pd


def create_bigquery_client():
    """Create a BigQuery client when optional dependencies are installed."""

    try:
        import google.cloud.bigquery  # noqa: F401
    except ImportError as exc:
        raise ImportError(
            "BigQuery source support requires optional dependencies. "
            "Install them with: pip install -r requirements-bigquery.txt"
        ) from exc

    raise NotImplementedError(
        "BigQuery source extraction is scaffolded but not fully configured yet. "
        "Set GOOGLE_APPLICATION_CREDENTIALS, BIGQUERY_PROJECT_ID, and "
        "BIGQUERY_DATASET before completing this connector."
    )


def load_bigquery_table(table_name):
    """Load a BigQuery table."""

    create_bigquery_client()


def get_bigquery_table_names():
    """Return BigQuery table names."""

    create_bigquery_client()


def get_bigquery_table_description(table_name):
    """Return BigQuery table metadata."""

    create_bigquery_client()


class BigQueryConnector:
    """Canonical BigQuery source connector placeholder."""

    def load_table(self, table_name: str) -> pd.DataFrame:
        """Load a BigQuery table."""

        return load_bigquery_table(table_name)

    def get_table_names(self) -> list[str]:
        """Return BigQuery table names."""

        return get_bigquery_table_names()

    def get_table_description(self, table_name: str) -> pd.DataFrame:
        """Return BigQuery table metadata."""

        return get_bigquery_table_description(table_name)

    def test_connection(self) -> bool:
        """Return whether BigQuery dependencies/configuration are available."""

        create_bigquery_client()
        return True
