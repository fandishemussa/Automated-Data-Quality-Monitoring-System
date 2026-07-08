from dashboard.actions import sanitize_command_output
from dashboard.permissions import can_export_reports, can_run_checks


def test_admin_and_analyst_can_export_reports():
    assert can_export_reports("admin")
    assert can_export_reports("analyst")


def test_viewer_cannot_export_or_run_checks():
    assert not can_export_reports("viewer")
    assert not can_run_checks("viewer")


def test_admin_and_analyst_can_run_checks():
    assert can_run_checks("admin")
    assert can_run_checks("analyst")


def test_sanitize_command_output_redacts_sensitive_lines():
    output = "\n".join([
        "Checks started",
        "DB_PASSWORD=super-secret",
        "Checks finished",
    ])

    sanitized = sanitize_command_output(output)

    assert "super-secret" not in sanitized
    assert "[redacted sensitive output line]" in sanitized
    assert "Checks finished" in sanitized
