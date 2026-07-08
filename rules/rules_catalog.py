"""Read-only rules catalog utilities for dashboard display."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from config.rule_loader import load_rules


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RULES_PATH = PROJECT_ROOT / "config" / "rules.yaml"
GLOBAL_SECTIONS = {"global_rules", "cross_table_validations", "quality_thresholds"}


def load_rules_catalog(file_path: str | Path = DEFAULT_RULES_PATH) -> dict[str, Any]:
    """Load active YAML rules for catalog display."""

    return load_rules(str(file_path))


def flatten_rules_for_display(rules: dict[str, Any]) -> list[dict[str, Any]]:
    """Flatten nested YAML rules into dashboard-friendly catalog rows."""

    rows: list[dict[str, Any]] = []

    for section_name, section_config in (rules or {}).items():
        if section_name == "global_rules":
            rows.extend(_flatten_global_rules(section_config))
        elif section_name == "cross_table_validations":
            rows.extend(_flatten_cross_table_validations(section_config))
        elif section_name == "quality_thresholds":
            rows.append(_row(
                dataset_name="GLOBAL",
                rule_type="quality_thresholds",
                column_name="",
                rule_config=section_config,
            ))
        else:
            rows.extend(_flatten_dataset_rules(section_name, section_config))

    return rows


def rules_to_yaml(rules: dict[str, Any]) -> str:
    """Return safely dumped YAML for read-only dashboard display."""

    return yaml.safe_dump(
        rules or {},
        sort_keys=False,
        allow_unicode=False,
        default_flow_style=False,
    )


def _flatten_dataset_rules(
    dataset_name: str,
    dataset_rules: Any,
) -> list[dict[str, Any]]:
    """Flatten one dataset's rule block."""

    if not isinstance(dataset_rules, dict):
        return [_row(dataset_name, "dataset_config", "", dataset_rules)]

    rows: list[dict[str, Any]] = []

    for rule_type, rule_config in dataset_rules.items():
        if isinstance(rule_config, list):
            rows.extend(
                _row(
                    dataset_name=dataset_name,
                    rule_type=rule_type,
                    column_name=str(item) if _is_scalar(item) else "",
                    rule_config=item,
                )
                for item in rule_config
            )
        elif isinstance(rule_config, dict):
            if rule_type == "custom_rules":
                rows.extend(
                    _row(
                        dataset_name=dataset_name,
                        rule_type=f"custom_rules.{custom_rule_name}",
                        column_name="",
                        rule_config=custom_rule_config,
                    )
                    for custom_rule_name, custom_rule_config in rule_config.items()
                )
            elif _looks_column_mapped(rule_config):
                rows.extend(
                    _row(
                        dataset_name=dataset_name,
                        rule_type=rule_type,
                        column_name=str(column_name),
                        rule_config=column_config,
                    )
                    for column_name, column_config in rule_config.items()
                )
            else:
                rows.append(_row(dataset_name, rule_type, "", rule_config))
        else:
            rows.append(_row(dataset_name, rule_type, "", rule_config))

    return rows


def _flatten_global_rules(global_rules: Any) -> list[dict[str, Any]]:
    """Flatten global rules into GLOBAL dataset rows."""

    if not isinstance(global_rules, dict):
        return [_row("GLOBAL", "global_rules", "", global_rules)]

    return [
        _row(
            dataset_name="GLOBAL",
            rule_type=rule_type,
            column_name="",
            rule_config=rule_config,
        )
        for rule_type, rule_config in global_rules.items()
    ]


def _flatten_cross_table_validations(validations: Any) -> list[dict[str, Any]]:
    """Flatten cross-table validation definitions."""

    if not isinstance(validations, list):
        return [_row("GLOBAL", "cross_table_validations", "", validations)]

    rows = []
    for index, validation in enumerate(validations, start=1):
        name = ""
        if isinstance(validation, dict):
            name = str(validation.get("name") or f"validation_{index}")
        rows.append(_row(
            dataset_name="GLOBAL",
            rule_type="cross_table_validation",
            column_name=name,
            rule_config=validation,
        ))
    return rows


def _row(
    dataset_name: str,
    rule_type: str,
    column_name: str,
    rule_config: Any,
) -> dict[str, Any]:
    """Build one flattened catalog row."""

    config = rule_config if rule_config is not None else {}
    return {
        "dataset_name": dataset_name,
        "rule_type": rule_type,
        "column_name": column_name or "",
        "rule_config": _config_to_text(config),
        "severity": _extract_config_value(config, "severity"),
        "enabled": _extract_enabled(config),
    }


def _looks_column_mapped(config: dict[str, Any]) -> bool:
    """Return whether a dictionary appears keyed by column/rule names."""

    control_keys = {
        "enabled",
        "severity",
        "description",
        "allowed_domains",
        "methods",
        "baseline_runs",
        "change_threshold_percent",
        "mean_change_threshold_percent",
        "std_change_threshold_percent",
        "psi_threshold",
        "z_score_threshold",
        "min_rows",
    }
    return not any(key in control_keys for key in config)


def _extract_config_value(config: Any, key: str) -> str:
    """Extract a scalar config value for a catalog column."""

    if isinstance(config, dict) and key in config:
        value = config.get(key)
        return "" if value is None else str(value)
    return ""


def _extract_enabled(config: Any) -> str:
    """Return enabled status for a rule row."""

    if isinstance(config, dict) and "enabled" in config:
        return str(bool(config.get("enabled")))
    return "True"


def _config_to_text(config: Any) -> str:
    """Serialize rule config for table display and CSV export."""

    if _is_scalar(config):
        return str(config)
    return json.dumps(config, default=str, sort_keys=True)


def _is_scalar(value: Any) -> bool:
    """Return True for simple scalar config values."""

    return isinstance(value, (str, int, float, bool)) or value is None
