import re

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL

from config.settings import DATABASE
from utils.logger import get_logger


logger = get_logger(__name__)

IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
DATA_TYPE_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_ ]*(\([0-9,\s]+\))?$")


def _validate_identifier(identifier, label="identifier"):
    """Validate table and column names before composing SQL statements."""

    if not isinstance(identifier, str) or not IDENTIFIER_PATTERN.match(identifier):
        raise ValueError(
            f"Invalid {label}: {identifier!r}. Use letters, numbers, and "
            "underscores only, and do not start with a number."
        )

    return identifier


def _quote_identifier(identifier, label="identifier"):
    """Return a safely quoted PostgreSQL identifier after validation."""

    return f'"{_validate_identifier(identifier, label)}"'


def _validate_data_type(data_type):
    """Validate simple SQL data types used by the helper DDL functions."""

    if not isinstance(data_type, str) or not DATA_TYPE_PATTERN.match(data_type):
        raise ValueError(
            f"Invalid SQL data type: {data_type!r}. Use a plain type such as "
            "TEXT, INTEGER, VARCHAR(255), NUMERIC(10, 2), or TIMESTAMP."
        )

    return data_type


def create_postgres_engine():
    """Create a SQLAlchemy engine using validated environment settings."""

    logger.debug(
        "Creating PostgreSQL engine for host=%s database=%s driver=%s.",
        DATABASE.host,
        DATABASE.database,
        DATABASE.drivername,
    )

    database_url = URL.create(
        drivername=DATABASE.drivername,
        username=DATABASE.username,
        password=DATABASE.password,
        host=DATABASE.host,
        port=DATABASE.port,
        database=DATABASE.database,
    )

    engine = create_engine(database_url)
    return engine


def load_table(table_name):
    engine = create_postgres_engine()
    table_identifier = _quote_identifier(table_name, "table name")
    query = text(f"SELECT * FROM {table_identifier}")
    df = pd.read_sql(query, engine)
    logger.debug("Loaded table %s with %s row(s).", table_name, len(df))
    return df


def get_table_names():
    engine = create_postgres_engine()
    query = text("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            """)
    df = pd.read_sql(query, engine)
    logger.debug("Loaded %s public table name(s) from PostgreSQL.", len(df))
    return df['table_name'].tolist()


def get_table_columns(table_name):
    engine = create_postgres_engine()
    query = text("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = :table_name
    """)
    df = pd.read_sql(query, engine, params={"table_name": table_name})
    logger.debug("Loaded %s column(s) for table %s.", len(df), table_name)
    return df['column_name'].tolist()


def get_table_dtypes(table_name):
    engine = create_postgres_engine()
    query = text("""
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = :table_name
    """)
    df = pd.read_sql(query, engine, params={"table_name": table_name})
    logger.debug("Loaded data types for table %s.", table_name)
    return df.set_index('column_name')['data_type'].to_dict()


def get_table_stats(table_name):
    engine = create_postgres_engine()
    table_identifier = _quote_identifier(table_name, "table name")
    query = text(f"SELECT COUNT(*) AS row_count FROM {table_identifier}")
    df = pd.read_sql(query, engine)
    logger.debug("Loaded row count for table %s.", table_name)
    return {"row_count": int(df.iloc[0]["row_count"])}


def get_table_null_count(table_name):
    engine = create_postgres_engine()
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


def get_table_distinct_count(table_name, column_name):
    engine = create_postgres_engine()
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


def get_table_distinct_values(table_name, column_name):
    engine = create_postgres_engine()
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


def get_table_sample(table_name, n=10):
    engine = create_postgres_engine()
    table_identifier = _quote_identifier(table_name, "table name")
    query = text(f"SELECT * FROM {table_identifier} LIMIT :limit")
    df = pd.read_sql(query, engine, params={"limit": int(n)})
    logger.debug("Loaded sample of %s row(s) from table %s.", len(df), table_name)
    return df


def get_table_description(table_name):
    engine = create_postgres_engine()
    query = text("""
        SELECT column_name, data_type, is_nullable
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = :table_name
    """)
    df = pd.read_sql(query, engine, params={"table_name": table_name})
    logger.debug("Loaded table description for %s.", table_name)
    return df


def get_table_size(table_name):
    engine = create_postgres_engine()
    query = text("""
        SELECT pg_size_pretty(pg_total_relation_size(to_regclass(:table_name)))
        AS table_size
    """)
    table_size = pd.read_sql(query, engine, params={"table_name": table_name}).iloc[0, 0]
    logger.debug("Loaded table size for %s: %s.", table_name, table_size)
    return table_size


def get_table_indexes(table_name):
    engine = create_postgres_engine()
    query = text("""
        SELECT indexname, indexdef
        FROM pg_indexes
        WHERE schemaname = 'public'
          AND tablename = :table_name
    """)
    df = pd.read_sql(query, engine, params={"table_name": table_name})
    logger.debug("Loaded %s index record(s) for table %s.", len(df), table_name)
    return df


def get_table_foreign_keys(table_name):
    engine = create_postgres_engine()
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


def get_table_primary_keys(table_name):
    engine = create_postgres_engine()
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


def update_table(table_name, update_values, where_conditions):
    engine = create_postgres_engine()

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


def delete_table_rows(table_name, where_conditions):
    engine = create_postgres_engine()

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


def alter_table_add_column(table_name, column_name, data_type):
    engine = create_postgres_engine()
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


def alter_table_drop_column(table_name, column_name):
    engine = create_postgres_engine()
    table_identifier = _quote_identifier(table_name, "table name")
    column_identifier = _quote_identifier(column_name, "column name")
    query = text(f"ALTER TABLE {table_identifier} DROP COLUMN {column_identifier}")
    with engine.begin() as connection:
        connection.execute(query)
    logger.info("Dropped column %s from table %s.", column_name, table_name)
