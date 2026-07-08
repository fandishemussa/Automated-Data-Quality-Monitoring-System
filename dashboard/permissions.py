"""Role-based dashboard action permissions."""

from __future__ import annotations


EXPORT_ROLES = {"admin", "analyst"}
RUN_CHECK_ROLES = {"admin", "analyst"}
ALERT_EDIT_ROLES = {"admin"}
ALERT_RESOLVE_ROLES = {"admin", "analyst"}


def normalize_role(role: str | None) -> str:
    """Normalize dashboard role values for permission checks."""

    return str(role or "viewer").strip().lower()


def can_export_reports(role: str | None) -> bool:
    """Return whether a role can download executive reports."""

    return normalize_role(role) in EXPORT_ROLES


def can_run_checks(role: str | None) -> bool:
    """Return whether a role can trigger data quality checks."""

    return normalize_role(role) in RUN_CHECK_ROLES


def can_edit_alerts_for_role(role: str | None) -> bool:
    """Return whether a role can edit alert fields."""

    return normalize_role(role) in ALERT_EDIT_ROLES


def can_resolve_alerts_for_role(role: str | None) -> bool:
    """Return whether a role can resolve alerts."""

    return normalize_role(role) in ALERT_RESOLVE_ROLES
