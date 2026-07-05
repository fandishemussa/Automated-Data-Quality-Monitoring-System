# System Architecture

The Automated Data Quality Monitoring System is organized as a modular Python project. Each layer has a narrow responsibility so checks, reporting, alerts, dashboarding, and API access can evolve independently.

## High-Level Flow

```text
PostgreSQL or Redshift Source Tables
        |
        v
data_sources/source_factory.py
        |
        v
config/rules.yaml
config/lineage.yaml
config/sla_rules.yaml
config/alert_ownership.yaml
        |
        v
checks/rule_engine.py + checks/anomaly_checks.py + checks/drift_detection.py
        |
        +------------------------------+
        |                              |
        v                              v
reports/generate_report.py + sla/sla_checker.py       reports/data_profiler.py
        |                              |
        +---------------+--------------+
                        |
                        v
PostgreSQL Monitoring Tables
        |
        +------------------------------+
        |                              |
        v                              v
dashboard/app.py                 api/app.py
```

## Main Components

| Component | Responsibility |
|---|---|
| `config/settings.py` | Loads and validates environment variables. |
| `config/rule_loader.py` | Loads YAML rule configuration. |
| `config/lineage.yaml` | Defines table-level lineage relationships. |
| `config/sla_rules.yaml` | Defines dataset-level quality SLA thresholds. |
| `config/alert_ownership.yaml` | Maps datasets, severities, and check types to alert owners. |
| `data_sources/source_factory.py` | Selects PostgreSQL, Redshift, Snowflake, or BigQuery as the source connector. |
| `data_sources/postgres_connector.py` | Creates SQLAlchemy engine and reads PostgreSQL tables. |
| `data_sources/redshift_connector.py` | Loads source tables from Amazon Redshift. |
| `checks/rule_engine.py` | Runs deterministic data quality rules. |
| `checks/anomaly_checks.py` | Runs statistical anomaly checks. |
| `checks/drift_detection.py` | Runs profile-based drift checks for numeric and categorical columns. |
| `lineage/lineage_service.py` | Normalizes lineage metadata into source-to-target edges. |
| `sla/sla_checker.py` | Evaluates and saves dataset SLA compliance for each run. |
| `reports/generate_report.py` | Saves run summaries, results, and issue details. |
| `reports/data_profiler.py` | Creates column-level data profiles. |
| `alerts/alert_manager.py` | Creates owner-assigned alerts based on run summaries and failed results. |
| `notifications/slack_notifier.py` | Sends optional Slack webhook notifications. |
| `notifications/teams_notifier.py` | Sends optional Microsoft Teams webhook notifications. |
| `auth/dashboard_auth.py` | Protects the Streamlit dashboard with environment-based login. |
| `ui/theme.py` | Loads dashboard branding and injects enterprise CSS. |
| `ui/components.py` | Provides reusable metric cards, badges, empty states, and footer components. |
| `ui/charts.py` | Applies consistent Altair chart styling. |
| `dashboard/app.py` | Streamlit dashboard for monitoring, filtering, resolving alerts, and exports. |
| `api/app.py` | Optional FastAPI interface for monitoring data. |
| `database/init_db.py` | Creates required monitoring tables. |
| `database/seed_sample_data.py` | Creates sample source tables with valid and invalid records. |
| `cli.py` | Provides beginner-friendly command-line shortcuts. |

## Data Storage

The project uses PostgreSQL for monitoring outputs. Source tables can be loaded from PostgreSQL or Amazon Redshift.

Source tables:

- `customers`
- `orders`
- `products`

Monitoring tables:

- `data_quality_runs`
- `data_quality_results`
- `data_quality_issue_details`
- `data_quality_alerts`
- `data_profile_results`
- `data_quality_sla_results`
- `data_lineage_edges`

## Configuration

Secrets and environment-specific values live in `.env`. The file is ignored by Git. Use `.env.example` as a safe template.

Rules live in `config/rules.yaml`, which should be committed to version control so quality expectations are reviewed like application code.

Dataset SLA thresholds live in `config/sla_rules.yaml` and are evaluated after every monitoring run.

Dashboard authentication is controlled by `DASHBOARD_AUTH_ENABLED`, `DASHBOARD_USERNAME`, and `DASHBOARD_PASSWORD` in `.env`.

Dashboard branding is controlled by `APP_NAME`, `COMPANY_NAME`, `DASHBOARD_TITLE`, `DASHBOARD_THEME`, `BRAND_*` color settings, and optional logo paths.

Source extraction is controlled by `SOURCE_DB_TYPE`. Use `postgres` for the default local flow, `redshift` for Amazon Redshift, or the scaffolded `snowflake` and `bigquery` values when completing optional connectors.

Slack and Teams notifications are controlled by `SLACK_NOTIFICATIONS_ENABLED`, `SLACK_WEBHOOK_URL`, `TEAMS_NOTIFICATIONS_ENABLED`, and `TEAMS_WEBHOOK_URL`.

## Extension Points

- Add a new rule type in `checks/rule_engine.py`.
- Add another source connector in `data_sources/`.
- Add new dashboard sections in `dashboard/app.py`.
- Add new API endpoints in `api/app.py`.
- Add notification channels under `notifications/`.
