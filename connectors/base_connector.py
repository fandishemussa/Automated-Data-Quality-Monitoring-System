"""Compatibility wrapper for the canonical data_sources connector interface."""

from data_sources.base_connector import BaseConnector


SourceConnector = BaseConnector

__all__ = ["BaseConnector", "SourceConnector"]
