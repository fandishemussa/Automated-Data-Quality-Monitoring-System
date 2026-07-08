"""MongoDB source connector placeholder with optional dependency guidance."""

from __future__ import annotations

import pandas as pd


def create_mongodb_client():
    """Create a MongoDB client when optional dependencies are installed."""

    try:
        import pymongo  # noqa: F401
    except ImportError as exc:
        raise ImportError(
            "MongoDB source support requires optional dependencies. "
            "Install them with: pip install pymongo"
        ) from exc

    raise NotImplementedError(
        "MongoDB source extraction is scaffolded but not fully configured yet. "
        "Set MONGODB_URI, MONGODB_DATABASE, and collection names before "
        "completing this connector."
    )


def load_mongodb_table(table_name: str) -> pd.DataFrame:
    """Load a MongoDB collection as a table-like DataFrame."""

    create_mongodb_client()


def get_mongodb_table_names() -> list[str]:
    """Return MongoDB collection names."""

    create_mongodb_client()


def get_mongodb_table_description(table_name: str) -> pd.DataFrame:
    """Return MongoDB collection metadata."""

    create_mongodb_client()


class MongoDBConnector:
    """Canonical MongoDB source connector placeholder."""

    def load_table(self, table_name: str) -> pd.DataFrame:
        """Load a MongoDB collection."""

        return load_mongodb_table(table_name)

    def get_table_names(self) -> list[str]:
        """Return MongoDB collection names."""

        return get_mongodb_table_names()

    def get_table_description(self, table_name: str) -> pd.DataFrame:
        """Return MongoDB collection metadata."""

        return get_mongodb_table_description(table_name)

    def test_connection(self) -> bool:
        """Return whether MongoDB dependencies/configuration are available."""

        create_mongodb_client()
        return True
