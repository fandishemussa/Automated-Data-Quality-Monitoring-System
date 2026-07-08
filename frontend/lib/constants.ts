export const APP_NAME = "Data Quality Command Center"
export const APP_VERSION = process.env.NEXT_PUBLIC_APP_VERSION ?? "v2.3.0"
export const ENVIRONMENT_NAME = process.env.NEXT_PUBLIC_ENVIRONMENT_NAME ?? "Development"
export const API_TOKEN_STORAGE_KEY = "dq_api_key"
export const USER_ROLE_STORAGE_KEY = "dq_user_role"
export const USER_NAME_STORAGE_KEY = "dq_user_name"

export const ALERT_LIFECYCLE_STATUSES = [
  "OPEN",
  "ACKNOWLEDGED",
  "INVESTIGATING",
  "RESOLVED",
  "ESCALATED",
]

export const REMEDIATION_PERMISSIONS = {
  admin: [
    "view_issues",
    "assign_issues",
    "create_cleaning_job",
    "approve_cleaning_job",
    "execute_cleaning_job",
    "rollback_cleaning_job",
    "mark_false_positive",
    "ignore_issue",
    "resolve_issue",
    "update_issue_status",
  ],
  analyst: [
    "view_issues",
    "create_cleaning_job",
    "execute_approved_cleaning_job",
    "mark_false_positive",
    "ignore_issue",
    "resolve_issue",
    "update_issue_status",
  ],
  data_analyst: [
    "view_issues",
    "create_cleaning_job",
    "execute_approved_cleaning_job",
    "mark_false_positive",
    "ignore_issue",
    "resolve_issue",
    "update_issue_status",
  ],
  data_engineer: [
    "view_issues",
    "create_cleaning_job",
    "execute_approved_cleaning_job",
    "mark_false_positive",
    "ignore_issue",
    "resolve_issue",
    "update_issue_status",
  ],
  viewer: ["view_issues"],
} as const
