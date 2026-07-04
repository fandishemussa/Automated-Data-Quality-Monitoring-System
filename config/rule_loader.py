import yaml
from pathlib import Path


def load_rules(file_path="config/rules.yaml"):
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"Rules file not found: {file_path}")

    with open(path, "r", encoding="utf-8") as file:
        rules = yaml.safe_load(file)

    return rules