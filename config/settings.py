"""Lazy environment and database settings helpers.

This module intentionally does not validate database variables at import time.
Tests and utility modules can import settings safely without requiring a local
`.env`; callers validate only when they actually create a database connection.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = PROJECT_ROOT / ".env"


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
    """Load variables from `.env` if present."""

    load_dotenv(ENV_FILE)


def get_env(name: str, default: str | None = None, required: bool = False) -> str | None:
    """Read an environment variable lazily with optional validation."""

    _load_environment()
    value = os.getenv(name)

    if value is None or not str(value).strip():
        if required:
            raise SettingsError(
                f"Missing required environment variable: {name}. "
                f"Set it in your shell or add it to {ENV_FILE}."
            )
        return default

    return value


def get_bool_env(name: str, default: bool = False) -> bool:
    """Read a boolean environment variable."""

    value = get_env(name)
    if value is None:
        return default
    return str(value).strip().lower() in {"true", "1", "yes", "y", "on"}


def get_int_env(name: str, default: int) -> int:
    """Read an integer environment variable."""

    value = get_env(name)
    if value is None:
        return default

    try:
        return int(value)
    except ValueError as exc:
        raise SettingsError(f"{name} must be a valid integer. Current value: {value!r}.") from exc


def get_legacy_db_config() -> DatabaseSettings:
    """Return database settings from legacy DB_* variables."""

    return DatabaseSettings(
        username=str(get_env("DB_USER", required=True)),
        password=str(get_env("DB_PASSWORD", required=True)),
        host=str(get_env("DB_HOST", required=True)),
        port=get_int_env("DB_PORT", 5432),
        database=str(get_env("DB_NAME", required=True)),
        drivername=str(get_env("DB_DRIVER", "postgresql+psycopg2")),
    )


def get_source_db_config() -> DatabaseSettings:
    """Return source database settings, falling back to DB_* variables."""

    return _get_prefixed_db_config("SOURCE_DB")


def get_monitor_db_config() -> DatabaseSettings:
    """Return monitoring database settings, falling back to DB_* variables."""

    return _get_prefixed_db_config("MONITOR_DB")


def load_database_settings() -> DatabaseSettings:
    """Backward-compatible alias for legacy database settings."""

    return get_legacy_db_config()


def _get_prefixed_db_config(prefix: str) -> DatabaseSettings:
    """Read prefixed DB settings with DB_* fallback."""

    return DatabaseSettings(
        username=_get_db_field(prefix, "USER", required=True),
        password=_get_db_field(prefix, "PASSWORD", required=True),
        host=_get_db_field(prefix, "HOST", required=True),
        port=_get_db_port(prefix),
        database=_get_db_field(prefix, "NAME", required=True),
        drivername=_get_db_field(
            prefix,
            "DRIVER",
            required=False,
            default="postgresql+psycopg2",
        ),
    )


def _get_db_field(
    prefix: str,
    suffix: str,
    required: bool,
    default: str | None = None,
) -> str:
    """Read PREFIX_SUFFIX, falling back to DB_SUFFIX."""

    prefixed_name = f"{prefix}_{suffix}"
    legacy_name = f"DB_{suffix}"
    value = get_env(prefixed_name)

    if value is not None:
        return value

    return str(get_env(legacy_name, default=default, required=required))


def _get_db_port(prefix: str) -> int:
    """Read a prefixed DB port with DB_PORT fallback."""

    prefixed_port = get_env(f"{prefix}_PORT")
    if prefixed_port is not None:
        try:
            return int(prefixed_port)
        except ValueError as exc:
            raise SettingsError(
                f"{prefix}_PORT must be a valid integer. Current value: {prefixed_port!r}."
            ) from exc

    return get_int_env("DB_PORT", 5432)
