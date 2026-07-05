"""Compatibility factory for source connector selection."""

from data_sources.source_factory import (
    SourceFunctions,
    get_source_functions,
    get_source_module_name,
    get_source_type,
)


def get_connector(source_type: str | None = None) -> SourceFunctions:
    """Return the configured source connector functions."""

    return get_source_functions(source_type)


__all__ = [
    "SourceFunctions",
    "get_connector",
    "get_source_functions",
    "get_source_module_name",
    "get_source_type",
]
