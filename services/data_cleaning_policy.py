"""Data cleaning safety policy loading and permission helpers."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from config.settings import PROJECT_ROOT


POLICY_PATH = PROJECT_ROOT / "config" / "data_cleaning_policy.yaml"

ROLE_PERMISSIONS: dict[str, set[str]] = {
    "admin": {
        "view_issues",
        "assign_issues",
        "create_cleaning_job",
        "approve_cleaning_job",
        "execute_cleaning_job",
        "rollback_cleaning_job",
        "mark_false_positive",
        "ignore_issue",
        "resolve_issue",
        "update_issue_status",
    },
    "analyst": {
        "view_issues",
        "create_cleaning_job",
        "execute_approved_cleaning_job",
        "mark_false_positive",
        "ignore_issue",
        "resolve_issue",
        "update_issue_status",
    },
    "data_analyst": {
        "view_issues",
        "create_cleaning_job",
        "execute_approved_cleaning_job",
        "mark_false_positive",
        "ignore_issue",
        "resolve_issue",
        "update_issue_status",
    },
    "data_engineer": {
        "view_issues",
        "create_cleaning_job",
        "execute_approved_cleaning_job",
        "mark_false_positive",
        "ignore_issue",
        "resolve_issue",
        "update_issue_status",
    },
    "viewer": {"view_issues"},
}


@lru_cache(maxsize=1)
def load_data_cleaning_policy() -> dict[str, Any]:
    """Load data cleaning policy from YAML with conservative defaults."""

    defaults = {
        "enabled": True,
        "require_approval_for_all": True,
        "allow_source_updates": False,
        "allow_delete_rows": False,
        "max_rows_per_job": 100,
        "allowed_actions": [],
        "restricted_actions": ["delete_row", "bulk_update"],
        "high_risk_actions": [],
        "role_policy": {},
    }

    if not POLICY_PATH.exists():
        return defaults

    with POLICY_PATH.open("r", encoding="utf-8") as file:
        loaded = yaml.safe_load(file) or {}

    return {**defaults, **loaded}


def normalize_role(role: str | None) -> str:
    """Normalize user role values used by API and frontend."""

    normalized = str(role or "viewer").strip().lower()
    if normalized == "data analyst":
        return "data_analyst"
    return normalized or "viewer"


def has_permission(role: str | None, permission: str) -> bool:
    """Return whether the role has a named remediation permission."""

    return permission in ROLE_PERMISSIONS.get(normalize_role(role), set())


def can_execute_without_approval(role: str | None) -> bool:
    """Return whether a role can execute low-risk jobs without approval."""

    policy = load_data_cleaning_policy()
    role_policy = policy.get("role_policy", {})
    return bool(role_policy.get(normalize_role(role), {}).get("can_execute_without_approval", False))


def is_action_allowed(action: str) -> bool:
    """Return whether an action is allowed by policy."""

    policy = load_data_cleaning_policy()
    allowed = set(policy.get("allowed_actions", []))
    restricted = set(policy.get("restricted_actions", []))
    return action in allowed and action not in restricted


def is_high_risk_action(action: str) -> bool:
    """Return whether an action requires extra review."""

    return action in set(load_data_cleaning_policy().get("high_risk_actions", []))
