"""Snowflake source connector scaffold with clear optional dependency guidance."""


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
