import json

import pandas as pd

from checks.drift_detection import calculate_psi, run_advanced_drift_checks


def test_calculate_psi_returns_zero_for_matching_distributions():
    expected = {"A": 50, "B": 50}
    actual = {"A": 0.5, "B": 0.5}

    assert calculate_psi(expected, actual) == 0


def test_calculate_psi_detects_distribution_shift():
    expected = {"A": 0.5, "B": 0.5}
    actual = {"A": 0.9, "B": 0.1}

    assert calculate_psi(expected, actual) > 0.2


def test_numeric_drift_detection_flags_mean_shift():
    current_df = pd.DataFrame({"amount": [20.0, 22.0, 24.0, 26.0]})
    historical_profiles = pd.DataFrame([
        {
            "run_id": 1,
            "dataset_name": "orders",
            "column_name": "amount",
            "mean": 10.0,
            "std_dev": 2.0,
            "value_distribution": None,
        }
    ])
    drift_config = {
        "enabled": True,
        "baseline_runs": 3,
        "mean_change_threshold_percent": 25,
        "std_change_threshold_percent": 30,
        "psi_threshold": 0.2,
    }

    results = run_advanced_drift_checks(
        df=current_df,
        dataset_name="orders",
        drift_config=drift_config,
        historical_profiles=historical_profiles,
    )

    mean_result = next(
        result for result in results
        if result["rule"].startswith("mean_change_percent_gt")
    )

    assert mean_result["status"] == "FAIL"
    assert mean_result["check_type"] == "data_drift_check"
    assert mean_result["column"] == "amount"

    detail_payload = json.loads(mean_result["details"][0]["sample_row"])
    assert detail_payload["drift_method"] == "mean_percentage_change"
    assert detail_payload["baseline_value"] == 10.0
    assert detail_payload["current_value"] == 23.0
    assert detail_payload["percent_change"] == 130.0
