"""PostgreSQL connector adapter for the common connector interface."""

from __future__ import annotations

from data_sources import postgres_connector


class PostgresConnector:
    """Adapter around the existing PostgreSQL source functions."""

    def create_engine_or_client(self):
        """Create the PostgreSQL SQLAlchemy engine."""

        return postgres_connector.create_source_engine()

    def load_table(self, table_name):
        """Load a PostgreSQL table."""

        return postgres_connector.load_table(table_name)

    def get_table_names(self):
        """Return PostgreSQL source table names."""

        return postgres_connector.get_table_names()

    def get_table_description(self, table_name):
        """Return PostgreSQL table metadata."""

        return postgres_connector.get_table_description(table_name)
