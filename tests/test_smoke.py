from pathlib import Path


def test_project_has_readme():
    assert Path("README.md").exists()


def test_rules_yaml_exists():
    assert Path("config/rules.yaml").exists()


def test_main_file_exists():
    assert Path("main.py").exists()