"""Application settings loaded from environment variables.

This module is the single place where database configuration is read. It keeps
connection details out of the codebase and gives a clear error when `.env` is
missing required values.
"""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = PROJECT_ROOT / ".env"

REQUIRED_DATABASE_ENV_VARS = (
    "DB_USER",
    "DB_PASSWORD",
    "DB_HOST",
    "DB_PORT",
    "DB_NAME",
)


class SettingsError(RuntimeError):
    """Raised when required project configuration is missing or invalid."""


@dataclass(frozen=True)
class DatabaseSettings:
    """Database connection settings used by SQLAlchemy."""

    username: str
    password: str
    host: str
    port: int
    database: str
    drivername: str = "postgresql+psycopg2"


def _load_environment() -> None:
    """Load variables from the project `.env` file if it exists."""

    load_dotenv(ENV_FILE)


def _validate_required_env_vars() -> None:
    missing_vars = [
        var_name
        for var_name in REQUIRED_DATABASE_ENV_VARS
        if not os.getenv(var_name) or not os.getenv(var_name, "").strip()
    ]

    if missing_vars:
        missing_list = ", ".join(missing_vars)
        raise SettingsError(
            "Missing required database environment variable(s): "
            f"{missing_list}. Add them to {ENV_FILE} or set them in your shell. "
            "Use .env.example as a template."
        )


def _get_database_port() -> int:
    raw_port = os.getenv("DB_PORT", "").strip()

    try:
        return int(raw_port)
    except ValueError as exc:
        raise SettingsError(
            f"DB_PORT must be a valid integer. Current value: {raw_port!r}."
        ) from exc


def load_database_settings() -> DatabaseSettings:
    """Load and validate PostgreSQL settings from environment variables."""

    _load_environment()
    _validate_required_env_vars()

    return DatabaseSettings(
        username=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        host=os.environ["DB_HOST"],
        port=_get_database_port(),
        database=os.environ["DB_NAME"],
        drivername=os.getenv("DB_DRIVER") or "postgresql+psycopg2",
    )


DATABASE = load_database_settings()
