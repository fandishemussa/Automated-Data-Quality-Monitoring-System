# Data Governance Framework

This project models a lightweight data governance workflow for operational data quality monitoring. It focuses on repeatable checks, transparent rules, auditable issue details, and clear alert handling.

## Governance Goals

- Define data quality expectations in version-controlled YAML rules.
- Run checks consistently across key datasets.
- Store every run, result, issue example, and alert in PostgreSQL.
- Give analysts and engineers enough detail to investigate root causes.
- Keep configuration and secrets outside source code.

## Roles And Responsibilities

| Role | Responsibility |
|---|---|
| Data Owner | Defines business expectations and acceptable thresholds. |
| Data Steward | Reviews failures, resolves alerts, and tracks recurring issues. |
| Data Engineer | Maintains pipelines, source tables, and monitoring code. |
| Analyst | Uses profiling and issue details to understand data reliability. |

## Quality Dimensions

| Dimension | Meaning | Example Check |
|---|---|---|
| Completeness | Required values are present. | `not_null_columns` |
| Uniqueness | Identifiers are not duplicated. | `unique_columns` |
| Validity | Values match expected patterns or ranges. | `format_checks`, `range_checks` |
| Freshness | Data is recent enough for use. | `freshness` |
| Consistency | Values agree across related tables. | `referential_integrity` |
| Accuracy | Values are plausible for the business process. | range, categorical, anomaly checks |

## Governance Workflow

1. Define rules in `config/rules.yaml`.
2. Initialize monitoring tables with `python database/init_db.py`.
3. Run checks with `python main.py` or `python cli.py run-checks`.
4. Review results and issue details in Streamlit.
5. Resolve alerts after investigation.
6. Update rules or upstream pipelines when recurring issues are found.

## Evidence And Auditability

The system keeps a record of each run in:

- `data_quality_runs`
- `data_quality_results`
- `data_quality_issue_details`
- `data_quality_alerts`
- `data_profile_results`

These tables make it possible to show when a problem started, which rule failed, how severe it was, and which sample rows were affected.
