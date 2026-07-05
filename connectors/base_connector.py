"""Common connector interface for source systems."""

from __future__ import annotations

from typing import Protocol

import pandas as pd


class SourceConnector(Protocol):
    """Interface implemented by source database connectors."""

    def create_engine_or_client(self):
        """Create the database engine or client object."""

    def load_table(self, table_name: str) -> pd.DataFrame:
        """Load a source table into a DataFrame."""

    def get_table_names(self) -> list[str]:
        """Return available source table names."""

    def get_table_description(self, table_name: str) -> pd.DataFrame:
        """Return metadata for a source table."""
