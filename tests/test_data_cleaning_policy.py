from services.data_cleaning_policy import (
    has_permission,
    is_high_risk_action,
    is_action_allowed,
    normalize_role,
)


def test_role_normalization_accepts_data_analyst_label():
    assert normalize_role("Data Analyst") == "data_analyst"


def test_viewer_has_view_only_permission():
    assert has_permission("viewer", "view_issues")
    assert not has_permission("viewer", "create_cleaning_job")


def test_admin_can_approve_and_rollback():
    assert has_permission("admin", "approve_cleaning_job")
    assert has_permission("admin", "rollback_cleaning_job")


def test_allowed_action_from_policy():
    assert is_action_allowed("replace_value")
    assert not is_action_allowed("delete_row")


def test_remediation_role_permissions_are_enforced():
    assert not has_permission("viewer", "create_cleaning_job")
    assert has_permission("analyst", "create_cleaning_job")
    assert has_permission("analyst", "execute_approved_cleaning_job")
    assert not has_permission("analyst", "approve_cleaning_job")
    assert has_permission("admin", "approve_cleaning_job")
    assert has_permission("admin", "rollback_cleaning_job")
    assert not has_permission("analyst", "rollback_cleaning_job")


def test_data_engineer_can_work_approved_remediation_without_admin_control():
    assert has_permission("data_engineer", "view_issues")
    assert has_permission("data_engineer", "create_cleaning_job")
    assert has_permission("data_engineer", "execute_approved_cleaning_job")
    assert not has_permission("data_engineer", "assign_issues")
    assert not has_permission("data_engineer", "approve_cleaning_job")


def test_issue_lifecycle_permissions():
    for role in ("admin", "analyst", "data_analyst", "data_engineer"):
        assert has_permission(role, "mark_false_positive")
        assert has_permission(role, "ignore_issue")
        assert has_permission(role, "resolve_issue")
        assert has_permission(role, "update_issue_status")

    assert not has_permission("viewer", "mark_false_positive")
    assert not has_permission("viewer", "ignore_issue")
    assert not has_permission("viewer", "resolve_issue")


def test_high_risk_actions_still_require_admin_approval_path():
    assert is_high_risk_action("regex_replace")
    assert not has_permission("analyst", "approve_cleaning_job")
