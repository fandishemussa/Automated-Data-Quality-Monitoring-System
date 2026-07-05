from notifications.slack_notifier import build_slack_message
from notifications.teams_notifier import build_teams_payload


def test_build_slack_message_includes_summary_and_owner():
    message = build_slack_message(
        run_id=42,
        summary={
            "overall_status": "FAIL",
            "quality_score": 81.5,
            "total_checks": 10,
            "failed_checks": 2,
            "critical_checks": 1,
        },
        alerts=[
            {
                "severity": "CRITICAL",
                "alert_type": "DATASET_QUALITY_FAILURE",
                "owner_team": "Data Platform",
                "message": "orders has failed checks.",
            }
        ],
    )

    assert "Run ID: 42" in message
    assert "Quality score: 81.5%" in message
    assert "Data Platform" in message
    assert "python -m streamlit run dashboard/app.py" in message


def test_build_teams_payload_includes_alert_facts_and_action():
    payload = build_teams_payload(
        run_id=43,
        summary={
            "quality_score": 90,
            "failed_checks": 1,
            "critical_checks": 0,
        },
        alerts=[
            {
                "severity": "HIGH",
                "alert_type": "DATA_QUALITY_FAILURE",
                "owner_team": "Operations Analytics",
                "message": "Run has failed checks.",
            }
        ],
    )

    assert payload["title"] == "Data Quality Alert"
    assert payload["sections"][0]["facts"][0]["value"] == "43"
    assert "Operations Analytics" in payload["sections"][1]["text"]
    assert "python -m streamlit run dashboard/app.py" in payload["sections"][2]["text"]
