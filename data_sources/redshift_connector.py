"""Amazon Redshift source connector using SQLAlchemy."""

from __future__ import annotations

import os
import re
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine, URL

from utils.logger import get_logger


PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")

logger = get_logger(__name__)

REDSHIFT_REQUIRED_ENV_VARS = (
    "REDSHIFT_HOST",
    "REDSHIFT_PORT",
    "REDSHIFT_DB",
    "REDSHIFT_USER",
    "REDSHIFT_PASSWORD",
)

IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def create_redshift_engine() -> Engine:
    """Create a SQLAlchemy engine for Amazon Redshift."""

    _validate_redshift_env()

    database_url = URL.create(
        drivername="postgresql+psycopg2",
        username=os.environ["REDSHIFT_USER"],
        password=os.environ["REDSHIFT_PASSWORD"],
        host=os.environ["REDSHIFT_HOST"],
        port=int(os.environ["REDSHIFT_PORT"]),
        database=os.environ["REDSHIFT_DB"],
    )

    logger.debug(
        "Creating Redshift engine for host=%s database=%s.",
        os.environ["REDSHIFT_HOST"],
        os.environ["REDSHIFT_DB"],
    )
    return create_engine(database_url)


def load_redshift_table(table_name: str) -> pd.DataFrame:
    """Load all rows from a validated Redshift table."""

    engine = create_redshift_engine()
    table_identifier = _qualified_table_identifier(table_name)
    query = text(f"SELECT * FROM {table_identifier}")
    df = pd.read_sql(query, engine)
    logger.debug("Loaded Redshift table %s with %s row(s).", table_name, len(df))
    return df


def get_redshift_table_names() -> list[str]:
    """Return table names from the configured Redshift schema."""

    engine = create_redshift_engine()
    schema = _redshift_schema()
    query = text("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = :schema
          AND table_type = 'BASE TABLE'
        ORDER BY table_name
    """)
    df = pd.read_sql(query, engine, params={"schema": schema})
    logger.debug("Loaded %s Redshift table name(s).", len(df))
    return df["table_name"].tolist()


def get_redshift_table_description(table_name: str) -> pd.DataFrame:
    """Return column metadata for a Redshift table."""

    engine = create_redshift_engine()
    schema = _redshift_schema()
    query = text("""
        SELECT column_name, data_type, is_nullable
        FROM information_schema.columns
        WHERE table_schema = :schema
          AND table_name = :table_name
        ORDER BY ordinal_position
    """)
    df = pd.read_sql(
        query,
        engine,
        params={"schema": schema, "table_name": table_name},
    )
    logger.debug("Loaded Redshift table description for %s.", table_name)
    return df


def _validate_redshift_env() -> None:
    """Raise a clear error when Redshift source settings are missing."""

    missing = [
        env_var
        for env_var in REDSHIFT_REQUIRED_ENV_VARS
        if not os.getenv(env_var, "").strip()
    ]

    if missing:
        missing_list = ", ".join(missing)
        raise RuntimeError(
            "SOURCE_DB_TYPE is set to redshift, but required Redshift "
            f"environment variable(s) are missing: {missing_list}. "
            "Add them to .env or switch SOURCE_DB_TYPE back to postgres."
        )

    try:
        int(os.environ["REDSHIFT_PORT"])
    except ValueError as exc:
        raise RuntimeError("REDSHIFT_PORT must be a valid integer.") from exc


def _redshift_schema() -> str:
    """Return the configured Redshift schema."""

    schema = os.getenv("REDSHIFT_SCHEMA", "public").strip() or "public"
    return _validate_identifier(schema, "schema name")


def _qualified_table_identifier(table_name: str) -> str:
    """Return a safely quoted Redshift schema-qualified table identifier."""

    schema = _redshift_schema()
    table = _validate_identifier(table_name, "table name")
    return f'"{schema}"."{table}"'


def _validate_identifier(identifier: str, label: str = "identifier") -> str:
    """Validate SQL identifiers before composing Redshift SQL."""

    if not isinstance(identifier, str) or not IDENTIFIER_PATTERN.match(identifier):
        raise ValueError(
            f"Invalid {label}: {identifier!r}. Use letters, numbers, and "
            "underscores only, and do not start with a number."
        )

    return identifier
