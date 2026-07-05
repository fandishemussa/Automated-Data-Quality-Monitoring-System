import re
from typing import Any

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine, URL

from config.settings import (
    DatabaseSettings,
    get_monitor_db_config,
    get_source_db_config,
)
from utils.logger import get_logger


logger = get_logger(__name__)

IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
DATA_TYPE_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_ ]*(\([0-9,\s]+\))?$")


def _validate_identifier(identifier: str, label: str = "identifier") -> str:
    """Validate table and column names before composing SQL statements."""

    if not isinstance(identifier, str) or not IDENTIFIER_PATTERN.match(identifier):
        raise ValueError(
            f"Invalid {label}: {identifier!r}. Use letters, numbers, and "
            "underscores only, and do not start with a number."
        )

    return identifier


def _quote_identifier(identifier: str, label: str = "identifier") -> str:
    """Return a safely quoted PostgreSQL identifier after validation."""

    return f'"{_validate_identifier(identifier, label)}"'


def _validate_data_type(data_type: str) -> str:
    """Validate simple SQL data types used by the helper DDL functions."""

    if not isinstance(data_type, str) or not DATA_TYPE_PATTERN.match(data_type):
        raise ValueError(
            f"Invalid SQL data type: {data_type!r}. Use a plain type such as "
            "TEXT, INTEGER, VARCHAR(255), NUMERIC(10, 2), or TIMESTAMP."
        )

    return data_type


def _create_engine_from_settings(settings: DatabaseSettings, label: str) -> Engine:
    """Create a SQLAlchemy engine from lazy database settings."""

    logger.debug(
        "Creating %s PostgreSQL engine for host=%s database=%s driver=%s.",
        label,
        settings.host,
        settings.database,
        settings.drivername,
    )

    database_url = URL.create(
        drivername=settings.drivername,
        username=settings.username,
        password=settings.password,
        host=settings.host,
        port=settings.port,
        database=settings.database,
    )

    return create_engine(database_url)


def create_source_engine() -> Engine:
    """Create the SQLAlchemy engine used to read source data tables."""

    return _create_engine_from_settings(get_source_db_config(), "source")


def create_monitor_engine() -> Engine:
    """Create the SQLAlchemy engine used for monitoring tables."""

    return _create_engine_from_settings(get_monitor_db_config(), "monitoring")


def create_postgres_engine() -> Engine:
    """Backward-compatible alias for the source PostgreSQL engine."""

    return create_source_engine()


def load_table(table_name: str) -> pd.DataFrame:
    """Load all rows from a validated PostgreSQL table name."""

    engine = create_source_engine()
    table_identifier = _quote_identifier(table_name, "table name")
    query = text(f"SELECT * FROM {table_identifier}")
    df = pd.read_sql(query, engine)
    logger.debug("Loaded table %s with %s row(s).", table_name, len(df))
    return df


def get_table_names() -> list[str]:
    """Return public table names from the connected PostgreSQL database."""

    engine = create_source_engine()
    query = text("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            """)
    df = pd.read_sql(query, engine)
    logger.debug("Loaded %s public table name(s) from PostgreSQL.", len(df))
    return df['table_name'].tolist()


def get_table_columns(table_name: str) -> list[str]:
    """Return column names for a public PostgreSQL table."""

    engine = create_source_engine()
    query = text("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = :table_name
    """)
    df = pd.read_sql(query, engine, params={"table_name": table_name})
    logger.debug("Loaded %s column(s) for table %s.", len(df), table_name)
    return df['column_name'].tolist()


def get_table_dtypes(table_name: str) -> dict[str, str]:
    """Return PostgreSQL data types keyed by column name."""

    engine = create_source_engine()
    query = text("""
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = :table_name
    """)
    df = pd.read_sql(query, engine, params={"table_name": table_name})
    logger.debug("Loaded data types for table %s.", table_name)
    return df.set_index('column_name')['data_type'].to_dict()


def get_table_stats(table_name: str) -> dict[str, int]:
    """Return simple row-count statistics for a table."""

    engine = create_source_engine()
    table_identifier = _quote_identifier(table_name, "table name")
    query = text(f"SELECT COUNT(*) AS row_count FROM {table_identifier}")
    df = pd.read_sql(query, engine)
    logger.debug("Loaded row count for table %s.", table_name)
    return {"row_count": int(df.iloc[0]["row_count"])}


def get_table_null_count(table_name: str) -> dict[str, Any]:
    """Return null counts for every column in a table."""

    engine = create_source_engine()
    table_identifier = _quote_identifier(table_name, "table name")
    columns = get_table_columns(table_name)

    if not columns:
        return {}

    null_count_columns = [
        f"SUM(CASE WHEN {_quote_identifier(column, 'column name')} IS NULL "
        f"THEN 1 ELSE 0 END) AS {_quote_identifier(column, 'column name')}"
        for column in columns
    ]
    query = text(f"SELECT {', '.join(null_count_columns)} FROM {table_identifier}")
    df = pd.read_sql(query, engine)
    logger.debug("Loaded null counts for table %s.", table_name)
    return df.iloc[0].to_dict()


def get_table_distinct_count(table_name: str, column_name: str) -> int:
    """Return distinct value count for one table column."""

    engine = create_source_engine()
    table_identifier = _quote_identifier(table_name, "table name")
    column_identifier = _quote_identifier(column_name, "column name")
    query = text(
        f"SELECT COUNT(DISTINCT {column_identifier}) AS distinct_count "
        f"FROM {table_identifier}"
    )
    distinct_count = pd.read_sql(query, engine).iloc[0, 0]
    logger.debug(
        "Loaded distinct count for %s.%s: %s",
        table_name,
        column_name,
        distinct_count,
    )
    return distinct_count


def get_table_distinct_values(table_name: str, column_name: str) -> list[Any]:
    """Return distinct values for one table column."""

    engine = create_source_engine()
    table_identifier = _quote_identifier(table_name, "table name")
    column_identifier = _quote_identifier(column_name, "column name")
    query = text(f"SELECT DISTINCT {column_identifier} FROM {table_identifier}")
    values = pd.read_sql(query, engine)[column_name].tolist()
    logger.debug(
        "Loaded %s distinct value(s) for %s.%s.",
        len(values),
        table_name,
        column_name,
    )
    return values


def get_table_sample(table_name: str, n: int = 10) -> pd.DataFrame:
    """Return a small sample of rows from a table."""

    engine = create_source_engine()
    table_identifier = _quote_identifier(table_name, "table name")
    query = text(f"SELECT * FROM {table_identifier} LIMIT :limit")
    df = pd.read_sql(query, engine, params={"limit": int(n)})
    logger.debug("Loaded sample of %s row(s) from table %s.", len(df), table_name)
    return df


def get_table_description(table_name: str) -> pd.DataFrame:
    """Return column metadata for a public table."""

    engine = create_source_engine()
    query = text("""
        SELECT column_name, data_type, is_nullable
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = :table_name
    """)
    df = pd.read_sql(query, engine, params={"table_name": table_name})
    logger.debug("Loaded table description for %s.", table_name)
    return df


def get_table_size(table_name: str) -> str:
    """Return PostgreSQL's human-readable total relation size."""

    engine = create_source_engine()
    query = text("""
        SELECT pg_size_pretty(pg_total_relation_size(to_regclass(:table_name)))
        AS table_size
    """)
    table_size = pd.read_sql(query, engine, params={"table_name": table_name}).iloc[0, 0]
    logger.debug("Loaded table size for %s: %s.", table_name, table_size)
    return table_size


def get_table_indexes(table_name: str) -> pd.DataFrame:
    """Return PostgreSQL index definitions for a table."""

    engine = create_source_engine()
    query = text("""
        SELECT indexname, indexdef
        FROM pg_indexes
        WHERE schemaname = 'public'
          AND tablename = :table_name
    """)
    df = pd.read_sql(query, engine, params={"table_name": table_name})
    logger.debug("Loaded %s index record(s) for table %s.", len(df), table_name)
    return df


def get_table_foreign_keys(table_name: str) -> pd.DataFrame:
    """Return foreign-key metadata for a table."""

    engine = create_source_engine()
    query = text("""
        SELECT
            conname,
            CAST(CAST(confrelid AS regclass) AS text) AS referenced_table,
            confkey,
            confupdtype
        FROM pg_constraint
        WHERE conrelid = to_regclass(:table_name)
          AND contype = 'f'
    """)
    df = pd.read_sql(query, engine, params={"table_name": table_name})
    logger.debug("Loaded %s foreign key record(s) for table %s.", len(df), table_name)
    return df


def get_table_primary_keys(table_name: str) -> pd.DataFrame:
    """Return primary-key column names for a table."""

    engine = create_source_engine()
    query = text("""
        SELECT a.attname
        FROM pg_index i
        JOIN pg_attribute a
          ON a.attrelid = i.indrelid
         AND a.attnum = ANY(i.indkey)
        WHERE i.indrelid = to_regclass(:table_name)
          AND i.indisprimary
    """)
    df = pd.read_sql(query, engine, params={"table_name": table_name})
    logger.debug("Loaded %s primary key record(s) for table %s.", len(df), table_name)
    return df


def update_table(
    table_name: str,
    update_values: dict[str, Any],
    where_conditions: dict[str, Any],
) -> int:
    """Update table rows using validated identifiers and bound values."""

    engine = create_source_engine()

    if not update_values:
        raise ValueError("update_values cannot be empty.")

    if not where_conditions:
        raise ValueError("where_conditions cannot be empty.")

    table_identifier = _quote_identifier(table_name, "table name")
    set_clause = ", ".join([
        f"{_quote_identifier(col, 'column name')} = :set_{col}"
        for col in update_values.keys()
    ])
    where_clause = " AND ".join([
        f"{_quote_identifier(col, 'column name')} = :where_{col}"
        for col in where_conditions.keys()
    ])

    query = text(f"UPDATE {table_identifier} SET {set_clause} WHERE {where_clause}")

    params = {}

    for col, val in update_values.items():
        params[f"set_{col}"] = val

    for col, val in where_conditions.items():
        params[f"where_{col}"] = val

    with engine.begin() as connection:
        result = connection.execute(query, params)
        logger.info(
            "Updated %s row(s) in table %s.",
            result.rowcount,
            table_name,
        )
        return result.rowcount


def delete_table_rows(table_name: str, where_conditions: dict[str, Any]) -> int:
    """Delete rows from a table using validated identifiers and bound values."""

    engine = create_source_engine()

    if not where_conditions:
        raise ValueError("where_conditions cannot be empty.")

    table_identifier = _quote_identifier(table_name, "table name")
    where_clause = " AND ".join([
        f"{_quote_identifier(col, 'column name')} = :{col}"
        for col in where_conditions.keys()
    ])
    query = text(f"DELETE FROM {table_identifier} WHERE {where_clause}")

    with engine.begin() as connection:
        result = connection.execute(query, where_conditions)
        logger.info(
            "Deleted %s row(s) from table %s.",
            result.rowcount,
            table_name,
        )
        return result.rowcount


def alter_table_add_column(table_name: str, column_name: str, data_type: str) -> None:
    """Add a column using validated identifiers and a simple SQL data type."""

    engine = create_source_engine()
    table_identifier = _quote_identifier(table_name, "table name")
    column_identifier = _quote_identifier(column_name, "column name")
    validated_data_type = _validate_data_type(data_type)
    query = text(
        f"ALTER TABLE {table_identifier} "
        f"ADD COLUMN {column_identifier} {validated_data_type}"
    )
    with engine.begin() as connection:
        connection.execute(query)
    logger.info("Added column %s to table %s.", column_name, table_name)


def alter_table_drop_column(table_name: str, column_name: str) -> None:
    """Drop a column using validated identifiers."""

    engine = create_source_engine()
    table_identifier = _quote_identifier(table_name, "table name")
    column_identifier = _quote_identifier(column_name, "column name")
    query = text(f"ALTER TABLE {table_identifier} DROP COLUMN {column_identifier}")
    with engine.begin() as connection:
        connection.execute(query)
    logger.info("Dropped column %s from table %s.", column_name, table_name)
