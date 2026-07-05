import pytest

from data_sources.source_factory import get_source_module_name, get_source_type


def test_get_source_type_defaults_to_postgres(monkeypatch):
    monkeypatch.delenv("SOURCE_DB_TYPE", raising=False)
    monkeypatch.delenv("DATA_SOURCE_TYPE", raising=False)

    assert get_source_type() == "postgres"


def test_get_source_module_name_selects_redshift():
    assert get_source_module_name("redshift") == "data_sources.redshift_connector"


def test_get_source_module_name_selects_optional_cloud_connectors():
    assert get_source_module_name("snowflake") == "data_sources.snowflake_connector"
    assert get_source_module_name("bigquery") == "data_sources.bigquery_connector"


def test_get_source_type_rejects_unknown_source():
    with pytest.raises(ValueError, match="Unsupported source database type"):
        get_source_type("oracle")
