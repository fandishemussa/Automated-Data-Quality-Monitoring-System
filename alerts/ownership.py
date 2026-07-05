"""Alert ownership mapping based on dataset, severity, and check type."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from utils.logger import get_logger


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OWNERSHIP_PATH = PROJECT_ROOT / "config" / "alert_ownership.yaml"
OWNER_FIELDS = ("owner_team", "owner_email", "slack_channel")
RESERVED_SECTIONS = {"default_owner", "severity_escalation", "check_type_ownership"}

logger = get_logger(__name__)


def load_alert_ownership_rules(
    file_path: str | Path = DEFAULT_OWNERSHIP_PATH,
) -> dict[str, Any]:
    """Load alert ownership rules from YAML configuration."""

    path = Path(file_path)
    if not path.is_absolute():
        path = PROJECT_ROOT / path

    if not path.exists():
        logger.warning("Alert ownership config not found: %s", path)
        return {}

    with path.open("r", encoding="utf-8") as file:
        rules = yaml.safe_load(file) or {}

    if not isinstance(rules, dict):
        raise ValueError("alert_ownership.yaml must contain a mapping.")

    return rules


def determine_alert_owner(
    dataset_name: str | None = None,
    severity: str | None = None,
    check_type: str | None = None,
    rules: dict[str, Any] | None = None,
) -> dict[str, str]:
    """Return the owner mapping for an alert."""

    ownership_rules = rules if rules is not None else load_alert_ownership_rules()

    owner = _clean_owner_mapping(ownership_rules.get("default_owner", {}))

    dataset_owner = _clean_owner_mapping(ownership_rules.get(str(dataset_name or ""), {}))
    if dataset_owner:
        owner.update(dataset_owner)

    check_type_owner = _clean_owner_mapping(
        ownership_rules.get("check_type_ownership", {}).get(str(check_type or ""), {})
    )
    if check_type_owner:
        owner.update(check_type_owner)

    severity_owner = _clean_owner_mapping(
        ownership_rules.get("severity_escalation", {}).get(
            str(severity or "").upper(),
            {},
        )
    )
    if severity_owner:
        owner.update(severity_owner)

    return {
        "owner_team": owner.get("owner_team", ""),
        "owner_email": owner.get("owner_email", ""),
        "slack_channel": owner.get("slack_channel", ""),
    }


def dataset_ownership_rules(rules: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return only dataset-level ownership sections from the full config."""

    ownership_rules = rules if rules is not None else load_alert_ownership_rules()
    return {
        key: value
        for key, value in ownership_rules.items()
        if key not in RESERVED_SECTIONS and isinstance(value, dict)
    }


def _clean_owner_mapping(mapping: Any) -> dict[str, str]:
    """Keep only known owner fields from an ownership config section."""

    if not isinstance(mapping, dict):
        return {}

    return {
        field: str(mapping.get(field, "") or "")
        for field in OWNER_FIELDS
        if mapping.get(field)
    }
