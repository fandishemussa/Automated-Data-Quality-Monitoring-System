import pandas as pd

from checks.volume_anomaly import (
    calculate_row_count_change,
    run_volume_anomaly_check,
)


CONFIG = {
    "enabled": True,
    "baseline_runs": 5,
    "change_threshold_percent": 40,
    "severity": "HIGH",
}


def _frame_with_rows(row_count):
    return pd.DataFrame({"id": list(range(row_count))})


def test_volume_anomaly_no_baseline_saves_history(monkeypatch):
    saved = {}

    monkeypatch.setattr(
        "checks.volume_anomaly.get_historical_row_counts",
        lambda dataset_name, baseline_runs: [],
    )

    def fake_save(**kwargs):
        saved.update(kwargs)
        return 1

    monkeypatch.setattr("checks.volume_anomaly.save_volume_history", fake_save)

    result = run_volume_anomaly_check(
        run_id=10,
        dataset_name="orders",
        current_df=_frame_with_rows(100),
        volume_config=CONFIG,
    )

    assert result["status"] == "SKIPPED"
    assert result["severity"] == "LOW"
    assert saved["row_count"] == 100
    assert saved["baseline_row_count"] == 100


def test_volume_anomaly_normal_change_passes(monkeypatch):
    saved = {}

    monkeypatch.setattr(
        "checks.volume_anomaly.get_historical_row_counts",
        lambda dataset_name, baseline_runs: [100, 110, 90],
    )
    monkeypatch.setattr(
        "checks.volume_anomaly.save_volume_history",
        lambda **kwargs: saved.update(kwargs) or 1,
    )

    result = run_volume_anomaly_check(
        run_id=11,
        dataset_name="orders",
        current_df=_frame_with_rows(120),
        volume_config=CONFIG,
    )

    assert result["status"] == "PASS"
    assert result["failed_rows"] == 0
    assert saved["status"] == "PASS"
    assert calculate_row_count_change(120, 100) == 20


def test_volume_anomaly_large_drop_fails(monkeypatch):
    monkeypatch.setattr(
        "checks.volume_anomaly.get_historical_row_counts",
        lambda dataset_name, baseline_runs: [100, 100, 100],
    )
    monkeypatch.setattr(
        "checks.volume_anomaly.save_volume_history",
        lambda **kwargs: 1,
    )

    result = run_volume_anomaly_check(
        run_id=12,
        dataset_name="orders",
        current_df=_frame_with_rows(50),
        volume_config=CONFIG,
    )

    assert result["status"] == "FAIL"
    assert result["severity"] == "HIGH"
    assert result["failed_rows"] == 1
    assert "drop" in result["details"][0]["reason"]
    assert calculate_row_count_change(50, 100) == -50


def test_volume_anomaly_large_spike_fails(monkeypatch):
    monkeypatch.setattr(
        "checks.volume_anomaly.get_historical_row_counts",
        lambda dataset_name, baseline_runs: [100, 100, 100],
    )
    monkeypatch.setattr(
        "checks.volume_anomaly.save_volume_history",
        lambda **kwargs: 1,
    )

    result = run_volume_anomaly_check(
        run_id=13,
        dataset_name="orders",
        current_df=_frame_with_rows(180),
        volume_config=CONFIG,
    )

    assert result["status"] == "FAIL"
    assert result["severity"] == "HIGH"
    assert result["failed_rows"] == 1
    assert "spike" in result["details"][0]["reason"]
    assert calculate_row_count_change(180, 100) == 80
