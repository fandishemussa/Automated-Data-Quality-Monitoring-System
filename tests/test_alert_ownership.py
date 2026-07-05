from alerts.ownership import determine_alert_owner


def test_determine_alert_owner_uses_dataset_owner():
    rules = {
        "customers": {
            "owner_team": "Data Governance",
            "owner_email": "data-governance@example.com",
        }
    }

    owner = determine_alert_owner(
        dataset_name="customers",
        severity="HIGH",
        check_type="not_null_check",
        rules=rules,
    )

    assert owner["owner_team"] == "Data Governance"
    assert owner["owner_email"] == "data-governance@example.com"


def test_determine_alert_owner_allows_severity_escalation_to_override_dataset():
    rules = {
        "orders": {
            "owner_team": "Operations Analytics",
            "owner_email": "ops-analytics@example.com",
        },
        "severity_escalation": {
            "CRITICAL": {
                "owner_team": "Data Platform",
                "owner_email": "data-platform@example.com",
            }
        },
    }

    owner = determine_alert_owner(
        dataset_name="orders",
        severity="CRITICAL",
        check_type="referential_integrity_check",
        rules=rules,
    )

    assert owner["owner_team"] == "Data Platform"
    assert owner["owner_email"] == "data-platform@example.com"


def test_determine_alert_owner_falls_back_to_check_type_then_default():
    rules = {
        "default_owner": {
            "owner_team": "Data Governance",
            "owner_email": "data-governance@example.com",
        },
        "check_type_ownership": {
            "data_drift_check": {
                "owner_team": "Analytics Engineering",
                "owner_email": "analytics-engineering@example.com",
            }
        },
    }

    owner = determine_alert_owner(
        dataset_name="unknown",
        severity="HIGH",
        check_type="data_drift_check",
        rules=rules,
    )

    assert owner["owner_team"] == "Analytics Engineering"
    assert owner["owner_email"] == "analytics-engineering@example.com"

    default_owner = determine_alert_owner(
        dataset_name="unknown",
        severity="LOW",
        check_type="unknown_check",
        rules=rules,
    )

    assert default_owner["owner_team"] == "Data Governance"
    assert default_owner["owner_email"] == "data-governance@example.com"
