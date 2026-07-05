"""Optional Snowflake connector placeholder."""


class SnowflakeConnector:
    """Placeholder that explains how to enable Snowflake support."""

    def create_engine_or_client(self):
        """Create a Snowflake connection when optional dependencies are installed."""

        try:
            import snowflake.connector  # noqa: F401
        except ImportError as exc:
            raise ImportError(
                "Snowflake support requires optional dependencies. "
                "Install them with: pip install -r requirements-snowflake.txt"
            ) from exc

        raise NotImplementedError(
            "Snowflake connection wiring is scaffolded but not enabled yet."
        )

    def load_table(self, table_name):
        """Load a Snowflake table."""

        self.create_engine_or_client()

    def get_table_names(self):
        """Return Snowflake table names."""

        self.create_engine_or_client()

    def get_table_description(self, table_name):
        """Return Snowflake table metadata."""

        self.create_engine_or_client()
