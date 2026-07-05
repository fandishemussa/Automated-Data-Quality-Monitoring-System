# Root Cause Analysis Guide

Root cause analysis starts with the failed check result and then moves into the example records stored in `data_quality_issue_details`.

## Investigation Flow

1. Open the Streamlit dashboard.
2. Select the latest failed `Run ID`.
3. Review `Overview` metrics and the quality score trend.
4. Open `Check Results` and filter by `FAIL`.
5. Open `Issue Details` for row-level examples.
6. Review `Alerts` and mark alerts as resolved after investigation.

## How Issue Details Help

Issue details store compact examples for failed checks:

| Field | Purpose |
|---|---|
| `dataset_name` | Identifies the source table. |
| `check_type` | Shows which rule failed. |
| `column_name` | Identifies the affected field. |
| `row_identifier` | Points to a likely row key or row index. |
| `bad_value` | Shows the invalid or missing value. |
| `reason` | Explains the failure in plain language. |
| `sample_row` | Gives enough context to reproduce the issue. |

## Common Root Causes

| Symptom | Possible Cause | Next Action |
|---|---|---|
| Nulls in required fields | Source system did not enforce mandatory input. | Check upstream validation and ingestion mappings. |
| Duplicate identifiers | Retry, merge, or deduplication issue. | Review primary key generation and batch load logic. |
| Invalid email format | Free-text input without validation. | Add validation in source app or ETL. |
| Negative amount or price | Refund logic, sign convention, or bad input. | Confirm business rules with data owner. |
| Referential integrity failure | Parent record missing or load order issue. | Check upstream dependencies and load sequencing. |
| Stale freshness check | Pipeline did not run or source stopped updating. | Check scheduler logs and source availability. |
| Drift or anomaly failure | Business volume changed or unexpected data spike. | Compare with releases, campaigns, incidents, or data fixes. |

## Alert Handling

Alerts should be resolved only after the issue is understood or accepted. Resolving an alert changes `data_quality_alerts.is_resolved` to `TRUE`; it does not delete the alert or modify the original check result.

Good alert notes for a ticket or runbook:

- Run ID
- Dataset and check type
- Number of failed rows
- Example row identifier
- Root cause
- Owner
- Follow-up action

## Escalation Guidance

Escalate when:

- A critical check fails.
- The quality score drops below an agreed threshold.
- A referential integrity failure affects reporting correctness.
- Drift or anomaly checks show unexplained large movement.
- The same issue repeats across multiple runs.
