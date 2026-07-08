from utils.audit_logger import build_audit_payload, log_audit_event


def test_build_audit_payload_serializes_values():
    payload = build_audit_payload(
        event_type="alert_edited",
        username=" admin ",
        role="admin",
        entity_type="alert",
        entity_id=123,
        old_value={"status": "OPEN"},
        new_value={"status": "RESOLVED"},
        ip_address="127.0.0.1",
    )

    assert payload["event_type"] == "ALERT_EDITED"
    assert payload["username"] == "admin"
    assert payload["entity_id"] == "123"
    assert '"status": "OPEN"' in payload["old_value"]
    assert '"status": "RESOLVED"' in payload["new_value"]


def test_log_audit_event_inserts_with_mocked_engine(monkeypatch):
    executed = {}

    class FakeConnection:
        def execute(self, statement, payload):
            executed["statement"] = statement
            executed["payload"] = payload

    class FakeBegin:
        def __enter__(self):
            return FakeConnection()

        def __exit__(self, exc_type, exc, traceback):
            return False

    class FakeEngine:
        def begin(self):
            return FakeBegin()

    monkeypatch.setattr(
        "utils.audit_logger.create_monitor_engine",
        lambda: FakeEngine(),
    )

    saved = log_audit_event(
        "USER_LOGIN",
        username="admin",
        role="admin",
        entity_type="dashboard_session",
        entity_id="admin",
    )

    assert saved is True
    assert executed["payload"]["event_type"] == "USER_LOGIN"
    assert executed["payload"]["username"] == "admin"


def test_log_audit_event_is_failure_safe(monkeypatch):
    class BrokenEngine:
        def begin(self):
            raise RuntimeError("database unavailable")

    monkeypatch.setattr(
        "utils.audit_logger.create_monitor_engine",
        lambda: BrokenEngine(),
    )

    assert log_audit_event("USER_LOGOUT", username="admin") is False
