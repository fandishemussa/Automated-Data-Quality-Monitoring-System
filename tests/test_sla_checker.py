from sla.sla_checker import evaluate_sla_for_run


def test_evaluate_sla_for_run_passes_when_thresholds_are_met():
    rules = {
        "customers": {
            "minimum_quality_score": 90,
            "max_critical_issues": 0,
            "max_failed_checks": 1,
            "freshness_hours": 24,
        }
    }
    results = [
        {
            "dataset_name": "customers",
            "check_type": "required_column_check",
            "status": "PASS",
            "severity": "NONE",
        },
        {
            "dataset_name": "customers",
            "check_type": "not_null_check",
            "status": "PASS",
            "severity": "NONE",
        },
    ]

    sla_results = evaluate_sla_for_run(10, results, rules)

    assert len(sla_results) == 1
    assert sla_results[0]["run_id"] == 10
    assert sla_results[0]["dataset_name"] == "customers"
    assert sla_results[0]["actual_quality_score"] == 100
    assert sla_results[0]["actual_failed_checks"] == 0
    assert sla_results[0]["actual_critical_issues"] == 0
    assert sla_results[0]["sla_status"] == "PASS"
    assert sla_results[0]["reason"] == "SLA met."


def test_evaluate_sla_for_run_fails_when_score_and_critical_thresholds_are_missed():
    rules = {
        "orders": {
            "minimum_quality_score": 80,
            "max_critical_issues": 0,
            "max_failed_checks": 1,
            "freshness_hours": 12,
        }
    }
    results = [
        {
            "dataset_name": "orders",
            "check_type": "required_column_check",
            "status": "PASS",
            "severity": "NONE",
        },
        {
            "dataset_name": "orders",
            "check_type": "referential_integrity_check",
            "status": "FAIL",
            "severity": "CRITICAL",
        },
        {
            "dataset_name": "orders",
            "check_type": "freshness_check",
            "status": "FAIL",
            "severity": "HIGH",
        },
    ]

    sla_results = evaluate_sla_for_run(11, results, rules)
    sla = sla_results[0]

    assert sla["actual_quality_score"] == 33.33
    assert sla["actual_failed_checks"] == 2
    assert sla["actual_critical_issues"] == 1
    assert sla["sla_status"] == "FAIL"
    assert "Quality score 33.33 is below required 80.0." in sla["reason"]
    assert "Critical issues 1 exceed allowed 0." in sla["reason"]
    assert "Failed checks 2 exceed allowed 1." in sla["reason"]
    assert "Freshness check failed" in sla["reason"]


def test_evaluate_sla_for_run_flags_configured_dataset_with_no_results():
    rules = {
        "products": {
            "minimum_quality_score": 90,
            "max_critical_issues": 0,
            "max_failed_checks": 3,
        }
    }

    sla_results = evaluate_sla_for_run(12, [], rules)
    sla = sla_results[0]

    assert sla["dataset_name"] == "products"
    assert sla["actual_quality_score"] == 0
    assert sla["sla_status"] == "FAIL"
    assert "No scored quality checks found" in sla["reason"]
