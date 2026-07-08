"""Canonical source connector interface."""

from __future__ import annotations

from abc import ABC, abstractmethod

import pandas as pd


class BaseConnector(ABC):
    """Base interface for all source data connectors."""

    @abstractmethod
    def load_table(self, table_name: str) -> pd.DataFrame:
        """Load a table into a pandas DataFrame."""

    @abstractmethod
    def get_table_names(self) -> list[str]:
        """Return available source table names."""

    @abstractmethod
    def get_table_description(self, table_name: str) -> pd.DataFrame:
        """Return source table metadata."""

    @abstractmethod
    def test_connection(self) -> bool:
        """Return whether the connector can reach its source."""
