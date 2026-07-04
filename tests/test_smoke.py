from pathlib import Path

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_project_has_required_files():
    """Check that core project files exist."""
    required_files = [
        "README.md",
        "main.py",
        "requirements.txt",
        "config/rules.yaml",
    ]

    for file_path in required_files:
        assert (PROJECT_ROOT / file_path).exists(), f"Missing required file: {file_path}"


def test_project_has_required_folders():
    """Check that core project folders exist."""
    required_folders = [
        "alerts",
        "checks",
        "config",
        "dashboard",
        "data_sources",
        "reports",
    ]

    for folder_path in required_folders:
        assert (PROJECT_ROOT / folder_path).exists(), f"Missing required folder: {folder_path}"


def test_rules_yaml_is_valid():
    """Check that config/rules.yaml is valid YAML."""
    rules_path = PROJECT_ROOT / "config" / "rules.yaml"

    with open(rules_path, "r", encoding="utf-8") as file:
        rules = yaml.safe_load(file)

    assert isinstance(rules, dict), "rules.yaml should contain a YAML dictionary"


def test_rules_yaml_contains_main_datasets():
    """Check that rules.yaml contains expected dataset sections."""
    rules_path = PROJECT_ROOT / "config" / "rules.yaml"

    with open(rules_path, "r", encoding="utf-8") as file:
        rules = yaml.safe_load(file)

    expected_sections = [
        "customers",
        "orders",
        "products",
        "global_rules",
        "quality_thresholds",
    ]

    for section in expected_sections:
        assert section in rules, f"Missing section in rules.yaml: {section}"


def test_dashboard_file_exists():
    """Check that Streamlit dashboard app exists."""
    dashboard_path = PROJECT_ROOT / "dashboard" / "app.py"

    assert dashboard_path.exists(), "Missing dashboard/app.py"


def test_database_connector_exists():
    """Check that PostgreSQL connector exists."""
    connector_path = PROJECT_ROOT / "data_sources" / "postgres_connector.py"

    assert connector_path.exists(), "Missing data_sources/postgres_connector.py"


def test_rule_engine_exists():
    """Check that rule engine exists."""
    rule_engine_path = PROJECT_ROOT / "checks" / "rule_engine.py"

    assert rule_engine_path.exists(), "Missing checks/rule_engine.py"