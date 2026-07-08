"""Failure-safe audit logging for dashboard and API actions."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import text

from data_sources.postgres_connector import create_monitor_engine
from utils.logger import get_logger


logger = get_logger(__name__)

INSERT_AUDIT_LOG_SQL = text(
    """
    INSERT INTO audit_logs (
        event_type,
        username,
        role,
        entity_type,
        entity_id,
        old_value,
        new_value,
        ip_address
    )
    VALUES (
        :event_type,
        :username,
        :role,
        :entity_type,
        :entity_id,
        :old_value,
        :new_value,
        :ip_address
    )
    """
)


def build_audit_payload(
    event_type: str,
    username: str | None = None,
    role: str | None = None,
    entity_type: str | None = None,
    entity_id: str | int | None = None,
    old_value: Any | None = None,
    new_value: Any | None = None,
    ip_address: str | None = None,
) -> dict[str, Any]:
    """Build a database-ready audit payload."""

    return {
        "event_type": str(event_type).strip().upper(),
        "username": _clean_text(username),
        "role": _clean_text(role),
        "entity_type": _clean_text(entity_type),
        "entity_id": None if entity_id is None else str(entity_id),
        "old_value": _serialize_value(old_value),
        "new_value": _serialize_value(new_value),
        "ip_address": _clean_text(ip_address),
    }


def log_audit_event(
    event_type: str,
    username: str | None = None,
    role: str | None = None,
    entity_type: str | None = None,
    entity_id: str | int | None = None,
    old_value: Any | None = None,
    new_value: Any | None = None,
    ip_address: str | None = None,
) -> bool:
    """Insert an audit event and never crash the calling action."""

    payload = build_audit_payload(
        event_type=event_type,
        username=username,
        role=role,
        entity_type=entity_type,
        entity_id=entity_id,
        old_value=old_value,
        new_value=new_value,
        ip_address=ip_address,
    )

    try:
        engine = create_monitor_engine()
        with engine.begin() as connection:
            connection.execute(INSERT_AUDIT_LOG_SQL, payload)
    except Exception:
        logger.exception("Could not write audit event %s.", payload["event_type"])
        return False

    logger.info("Audit event recorded: %s", payload["event_type"])
    return True


def _serialize_value(value: Any | None) -> str | None:
    """Serialize old/new values for text storage."""

    if value is None:
        return None

    if isinstance(value, str):
        return value

    try:
        return json.dumps(value, default=str, sort_keys=True)
    except TypeError:
        return str(value)


def _clean_text(value: Any | None) -> str | None:
    """Normalize optional text values."""

    if value is None:
        return None

    text_value = str(value).strip()
    return text_value or None
