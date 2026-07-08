import pytest

from data_sources.postgres_connector import PostgresConnector
from data_sources.source_factory import (
    get_source_connector,
    get_source_functions,
    get_source_module_name,
    get_source_type,
)


def test_get_source_type_defaults_to_postgres(monkeypatch):
    monkeypatch.delenv("SOURCE_DB_TYPE", raising=False)
    monkeypatch.delenv("DATA_SOURCE_TYPE", raising=False)

    assert get_source_type() == "postgres"


def test_get_source_module_name_selects_redshift():
    assert get_source_module_name("redshift") == "data_sources.redshift_connector"


def test_get_source_module_name_selects_optional_cloud_connectors():
    assert get_source_module_name("snowflake") == "data_sources.snowflake_connector"
    assert get_source_module_name("bigquery") == "data_sources.bigquery_connector"
    assert get_source_module_name("mongodb") == "data_sources.mongodb_connector"


def test_get_source_type_rejects_unknown_source():
    with pytest.raises(ValueError, match="Unsupported source database type"):
        get_source_type("oracle")


def test_factory_returns_postgres_connector():
    connector = get_source_connector("postgres")

    assert isinstance(connector, PostgresConnector)


def test_source_functions_include_test_connection():
    functions = get_source_functions("postgres")

    assert callable(functions.load_table)
    assert callable(functions.get_table_names)
    assert callable(functions.get_table_description)
    assert callable(functions.test_connection)


def test_optional_dependency_missing_message(monkeypatch):
    import builtins

    original_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "snowflake.connector":
            raise ImportError("missing snowflake")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    connector = get_source_connector("snowflake")
    with pytest.raises(ImportError, match="requirements-snowflake.txt"):
        connector.test_connection()
