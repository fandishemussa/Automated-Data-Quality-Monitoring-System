"""Amazon Redshift connector adapter for the common connector interface."""

from __future__ import annotations

from data_sources import redshift_connector


class RedshiftConnector:
    """Adapter around the Redshift source functions."""

    def create_engine_or_client(self):
        """Create the Redshift SQLAlchemy engine."""

        return redshift_connector.create_redshift_engine()

    def load_table(self, table_name):
        """Load a Redshift table."""

        return redshift_connector.load_redshift_table(table_name)

    def get_table_names(self):
        """Return Redshift source table names."""

        return redshift_connector.get_redshift_table_names()

    def get_table_description(self, table_name):
        """Return Redshift table metadata."""

        return redshift_connector.get_redshift_table_description(table_name)
