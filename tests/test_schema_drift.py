import pandas as pd

from checks.schema_drift import (
    compare_schema_snapshots,
    normalize_schema,
    run_schema_drift_check,
)


BASELINE_SCHEMA = [
    {
        "column_name": "customer_id",
        "data_type": "integer",
        "is_nullable": "NO",
        "ordinal_position": 1,
    },
    {
        "column_name": "email",
        "data_type": "character varying",
        "is_nullable": "YES",
        "ordinal_position": 2,
    },
]


def test_schema_drift_no_previous_snapshot_saves_baseline(monkeypatch):
    saved = {}

    monkeypatch.setattr(
        "checks.schema_drift.get_current_schema",
        lambda dataset_name: BASELINE_SCHEMA,
    )
    monkeypatch.setattr(
        "checks.schema_drift.load_previous_schema_snapshot",
        lambda dataset_name: [],
    )

    def fake_save(run_id, dataset_name, current_schema):
        saved["run_id"] = run_id
        saved["dataset_name"] = dataset_name
        saved["rows"] = current_schema
        return len(current_schema)

    monkeypatch.setattr("checks.schema_drift.save_schema_snapshot", fake_save)

    result = run_schema_drift_check(
        run_id=42,
        dataset_name="customers",
        drift_config={"enabled": True, "severity": "HIGH"},
    )

    assert result["status"] == "SKIPPED"
    assert result["severity"] == "LOW"
    assert saved["run_id"] == 42
    assert saved["dataset_name"] == "customers"
    assert len(saved["rows"]) == 2


def test_schema_drift_detects_added_column():
    current = BASELINE_SCHEMA + [{
        "column_name": "phone",
        "data_type": "text",
        "is_nullable": "YES",
        "ordinal_position": 3,
    }]

    changes = compare_schema_snapshots(current, BASELINE_SCHEMA)

    assert any(change["change_type"] == "added_column" for change in changes)
    assert any(change["column_name"] == "phone" for change in changes)


def test_schema_drift_detects_removed_column():
    current = [BASELINE_SCHEMA[0]]

    changes = compare_schema_snapshots(current, BASELINE_SCHEMA)

    assert any(change["change_type"] == "removed_column" for change in changes)
    assert any(change["column_name"] == "email" for change in changes)


def test_schema_drift_detects_changed_data_type():
    current = [
        BASELINE_SCHEMA[0],
        {
            "column_name": "email",
            "data_type": "text",
            "is_nullable": "YES",
            "ordinal_position": 2,
        },
    ]

    changes = compare_schema_snapshots(current, BASELINE_SCHEMA)

    assert any(change["change_type"] == "changed_data_type" for change in changes)
    assert any(change["current_value"] == "text" for change in changes)


def test_normalize_schema_assigns_ordinal_when_missing():
    rows = normalize_schema(
        schema_df=pd.DataFrame({
            "column_name": ["id", "name"],
            "data_type": ["INTEGER", "TEXT"],
            "is_nullable": ["NO", "YES"],
        })
    )

    assert rows[0]["ordinal_position"] == 1
    assert rows[0]["data_type"] == "integer"
    assert rows[1]["is_nullable"] == "YES"
