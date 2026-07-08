from datetime import datetime, timedelta

from alerts.escalation import (
    calculate_sla_due_at,
    is_alert_due_for_escalation,
    run_alert_escalation,
)


RULES = {
    "CRITICAL": {"after_hours": 4, "escalation_level": 1, "notify_team": "Data Platform"},
    "HIGH": {"after_hours": 24, "escalation_level": 1, "notify_team": "Data Governance"},
}


def test_due_critical_alert_escalates(monkeypatch):
    now = datetime(2026, 7, 6, 12, 0, 0)
    due_alert = {
        "id": 10,
        "run_id": 99,
        "severity": "CRITICAL",
        "message": "Critical failure",
        "created_at": now - timedelta(hours=5),
        "sla_due_at": now - timedelta(hours=1),
        "is_resolved": False,
    }
    escalated_ids = []

    monkeypatch.setattr("alerts.escalation._load_escalation_rules", lambda: RULES)
    monkeypatch.setattr(
        "alerts.escalation.find_alerts_to_escalate",
        lambda now=None, escalation_rules=None: [due_alert],
    )
    monkeypatch.setattr(
        "alerts.escalation.escalate_alert",
        lambda alert_id, escalation_status, escalation_level, sla_due_at: escalated_ids.append(alert_id) or True,
    )
    monkeypatch.setattr("alerts.escalation._send_escalation_notifications", lambda alerts: None)

    result = run_alert_escalation(now=now)

    assert escalated_ids == [10]
    assert len(result) == 1
    assert result[0]["escalation_status"] == "ESCALATED"


def test_resolved_alert_does_not_escalate():
    now = datetime(2026, 7, 6, 12, 0, 0)
    alert = {
        "severity": "CRITICAL",
        "created_at": now - timedelta(hours=10),
        "is_resolved": True,
    }

    assert not is_alert_due_for_escalation(alert, now, RULES)


def test_not_yet_due_alert_does_not_escalate():
    now = datetime(2026, 7, 6, 12, 0, 0)
    alert = {
        "severity": "HIGH",
        "created_at": now - timedelta(hours=2),
        "is_resolved": False,
    }

    assert not is_alert_due_for_escalation(alert, now, RULES)


def test_calculate_sla_due_at_uses_severity_rule():
    created_at = datetime(2026, 7, 6, 8, 0, 0)

    assert calculate_sla_due_at(created_at, "CRITICAL", RULES) == datetime(2026, 7, 6, 12, 0, 0)
