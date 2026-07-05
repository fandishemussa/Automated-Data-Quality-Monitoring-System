from pathlib import Path
from typing import Any

import yaml


def load_rules(file_path: str = "config/rules.yaml") -> dict[str, Any]:
    """Load YAML data quality rules from disk."""

    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"Rules file not found: {file_path}")

    with open(path, "r", encoding="utf-8") as file:
        rules = yaml.safe_load(file)

    return rules or {}
