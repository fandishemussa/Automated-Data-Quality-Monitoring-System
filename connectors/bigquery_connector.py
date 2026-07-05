"""Optional BigQuery connector placeholder."""


class BigQueryConnector:
    """Placeholder that explains how to enable BigQuery support."""

    def create_engine_or_client(self):
        """Create a BigQuery client when optional dependencies are installed."""

        try:
            import google.cloud.bigquery  # noqa: F401
        except ImportError as exc:
            raise ImportError(
                "BigQuery support requires optional dependencies. "
                "Install them with: pip install -r requirements-bigquery.txt"
            ) from exc

        raise NotImplementedError(
            "BigQuery connection wiring is scaffolded but not enabled yet."
        )

    def load_table(self, table_name):
        """Load a BigQuery table."""

        self.create_engine_or_client()

    def get_table_names(self):
        """Return BigQuery table names."""

        self.create_engine_or_client()

    def get_table_description(self, table_name):
        """Return BigQuery table metadata."""

        self.create_engine_or_client()
