import pandas as pd

from checks.rule_engine import (
    calculate_severity,
    check_categorical_rules,
    check_format_rules,
    check_not_null_columns,
    check_range_rules,
    check_unique_columns,
)


def test_check_not_null_columns_flags_missing_values():
    df = pd.DataFrame({
        "customer_id": [1, 2, 3],
        "email": ["one@example.com", None, "three@example.com"],
    })

    result = check_not_null_columns(df, "customers", ["email"])[0]

    assert result["status"] == "FAIL"
    assert result["failed_rows"] == 1
    assert result["failure_rate"] == 0.3333
    assert result["details"][0]["bad_value"] == "NULL"


def test_check_not_null_columns_handles_missing_column():
    df = pd.DataFrame({"customer_id": [1, 2, 3]})

    result = check_not_null_columns(df, "customers", ["email"])[0]

    assert result["status"] == "FAIL"
    assert result["column"] == "email"
    assert "missing" in result["details"][0]["reason"].lower()


def test_check_unique_columns_flags_duplicate_values():
    df = pd.DataFrame({
        "customer_id": [1, 2, 3],
        "email": ["same@example.com", "same@example.com", "unique@example.com"],
    })

    result = check_unique_columns(df, "customers", ["email"])[0]

    assert result["status"] == "FAIL"
    assert result["failed_rows"] == 1
    assert len(result["details"]) == 2


def test_check_format_rules_flags_invalid_email_and_ignores_null():
    df = pd.DataFrame({
        "customer_id": [1, 2, 3],
        "email": ["good@example.com", "not-an-email", None],
    })

    result = check_format_rules(df, "customers", {"email": "email"})[0]

    assert result["status"] == "FAIL"
    assert result["failed_rows"] == 1
    assert result["details"][0]["bad_value"] == "not-an-email"


def test_check_range_rules_flags_numeric_values_outside_bounds():
    df = pd.DataFrame({
        "order_id": [1, 2, 3, 4],
        "amount": [10.0, -5.0, 100.0, 2000.0],
    })

    result = check_range_rules(
        df,
        "orders",
        {"amount": {"min": 0, "max": 1000}},
    )[0]

    assert result["status"] == "FAIL"
    assert result["failed_rows"] == 2
    assert result["severity"] == "HIGH"


def test_check_categorical_rules_flags_unexpected_values():
    df = pd.DataFrame({
        "order_id": [1, 2, 3],
        "status": ["pending", "delivered", "unknown"],
    })

    result = check_categorical_rules(
        df,
        "orders",
        {"status": {"allowed_values": ["pending", "delivered"]}},
    )[0]

    assert result["status"] == "FAIL"
    assert result["failed_rows"] == 1
    assert result["details"][0]["bad_value"] == "unknown"


def test_calculate_severity_uses_check_type_and_failure_rate():
    assert calculate_severity("required_column_check", "FAIL", 1.0) == "CRITICAL"
    assert calculate_severity("not_null_check", "FAIL", 0.10) == "HIGH"
    assert calculate_severity("not_null_check", "FAIL", 0.20) == "CRITICAL"
    assert calculate_severity("format_check", "FAIL", 0.01) == "LOW"
    assert calculate_severity("format_check", "FAIL", 0.10) == "MEDIUM"
    assert calculate_severity("format_check", "FAIL", 0.50) == "HIGH"
    assert calculate_severity("format_check", "PASS", 0.0) == "NONE"
    assert calculate_severity("data_drift_check", "SKIPPED", 0.0) == "LOW"
