import json

from rules.rules_catalog import flatten_rules_for_display


def test_flatten_rules_for_display_column_lists():
    rules = {
        "customers": {
            "required_columns": ["customer_id", "email"],
            "not_null_columns": ["customer_id"],
        }
    }

    rows = flatten_rules_for_display(rules)

    assert len(rows) == 3
    assert {
        "dataset_name": "customers",
        "rule_type": "required_columns",
        "column_name": "email",
        "rule_config": "email",
        "severity": "",
        "enabled": "True",
    } in rows


def test_flatten_rules_for_display_column_mapped_config():
    rules = {
        "orders": {
            "range_checks": {
                "amount": {"min": 0, "max": 1000, "severity": "HIGH"}
            }
        }
    }

    rows = flatten_rules_for_display(rules)

    assert len(rows) == 1
    assert rows[0]["dataset_name"] == "orders"
    assert rows[0]["rule_type"] == "range_checks"
    assert rows[0]["column_name"] == "amount"
    assert rows[0]["severity"] == "HIGH"
    assert json.loads(rows[0]["rule_config"])["max"] == 1000


def test_flatten_rules_for_display_global_enabled_rule():
    rules = {
        "global_rules": {
            "volume_anomaly_detection": {
                "enabled": False,
                "baseline_runs": 5,
                "severity": "HIGH",
            }
        }
    }

    rows = flatten_rules_for_display(rules)

    assert rows == [{
        "dataset_name": "GLOBAL",
        "rule_type": "volume_anomaly_detection",
        "column_name": "",
        "rule_config": '{"baseline_runs": 5, "enabled": false, "severity": "HIGH"}',
        "severity": "HIGH",
        "enabled": "False",
    }]


def test_flatten_rules_for_display_custom_rules_are_named():
    rules = {
        "customers": {
            "custom_rules": {
                "email_domains": {
                    "allowed_domains": ["company.com"],
                    "severity": "MEDIUM",
                }
            }
        }
    }

    rows = flatten_rules_for_display(rules)

    assert rows[0]["dataset_name"] == "customers"
    assert rows[0]["rule_type"] == "custom_rules.email_domains"
    assert rows[0]["severity"] == "MEDIUM"


def test_flatten_rules_for_display_cross_table_validations():
    rules = {
        "cross_table_validations": [{
            "name": "customer_order_relationship",
            "validation": {
                "source_table": "orders",
                "target_table": "customers",
            },
        }]
    }

    rows = flatten_rules_for_display(rules)

    assert len(rows) == 1
    assert rows[0]["dataset_name"] == "GLOBAL"
    assert rows[0]["rule_type"] == "cross_table_validation"
    assert rows[0]["column_name"] == "customer_order_relationship"
