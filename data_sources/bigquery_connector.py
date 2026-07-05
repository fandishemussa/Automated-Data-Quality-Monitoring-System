"""BigQuery source connector scaffold with clear optional dependency guidance."""


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
