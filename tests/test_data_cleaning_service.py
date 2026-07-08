import pytest

from services.data_cleaning_service import (
    build_proposed_change_rows,
    build_change_log_payload,
    parse_row_identifier,
    suggest_cleaning_actions,
    update_issue_status,
)


def test_suggest_cleaning_actions_for_email_format_issue():
    issue = {
        "check_type": "format_check",
        "column_name": "email",
        "reason": "Invalid email",
    }

    actions = {item["action"] for item in suggest_cleaning_actions(issue)}

    assert "trim_whitespace" in actions
    assert "lowercase" in actions
    assert "replace_value" in actions


def test_suggest_cleaning_actions_for_range_issue():
    issue = {"check_type": "range_check", "column_name": "amount", "reason": "too high"}

    actions = {item["action"] for item in suggest_cleaning_actions(issue)}

    assert "cap_to_min" in actions
    assert "cap_to_max" in actions


def test_parse_row_identifier_column_equals_value():
    assert parse_row_identifier("customer_id=123") == {"customer_id": "123"}


def test_parse_row_identifier_json_object():
    assert parse_row_identifier('{"order_id": 42}') == {"order_id": 42}


def test_parse_row_identifier_rejects_empty():
    with pytest.raises(ValueError):
        parse_row_identifier("")


def test_build_change_log_payload_serializes_values():
    payload = build_change_log_payload(
        job_id=1,
        dataset_name="customers",
        table_name="customers",
        column_name="email",
        row_identifier="customer_id=1",
        old_value="OLD@EXAMPLE.COM",
        new_value="old@example.com",
        change_reason="lowercase",
    )

    assert payload["old_value"] == "OLD@EXAMPLE.COM"
    assert payload["new_value"] == "old@example.com"
    assert payload["change_reason"] == "lowercase"


def test_build_proposed_change_rows_from_preview_json():
    rows = build_proposed_change_rows(
        {
            "id": 7,
            "dataset_name": "customers",
            "target_table": "customers",
            "target_column": "email",
            "row_identifier": "customer_id=1",
            "cleaning_action": "lowercase",
            "preview_rows": (
                '[{"row_identifier":"customer_id=1","old_value":"OLD@EXAMPLE.COM",'
                '"new_value":"old@example.com","will_update":true}]'
            ),
        }
    )

    assert rows[0]["job_id"] == 7
    assert rows[0]["old_value"] == "OLD@EXAMPLE.COM"
    assert rows[0]["new_value"] == "old@example.com"
    assert rows[0]["change_reason"] == "PROPOSED_lowercase"


def test_update_issue_status_rejects_invalid_status_before_db_lookup():
    with pytest.raises(ValueError):
        update_issue_status(1, "NOT_A_STATUS", "tester")
