"""Load data lineage configuration from YAML."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LINEAGE_CONFIG = PROJECT_ROOT / "config" / "lineage.yaml"


def load_lineage_config(file_path: str | Path = DEFAULT_LINEAGE_CONFIG) -> dict[str, Any]:
    """Load table lineage metadata from a YAML file."""

    path = Path(file_path)

    if not path.is_absolute():
        path = PROJECT_ROOT / path

    if not path.exists():
        raise FileNotFoundError(f"Lineage config file not found: {path}")

    with open(path, "r", encoding="utf-8") as file:
        lineage_config = yaml.safe_load(file) or {}

    if not isinstance(lineage_config, dict):
        raise ValueError("Lineage config must be a YAML dictionary.")

    return lineage_config
