# Automated Data Quality Monitoring System

Automated Data Quality Monitoring System is a Python portfolio project for validating PostgreSQL data with configurable YAML rules, storing run history, tracking issue details, generating alerts, and visualizing data health in a Streamlit dashboard.

The project is designed to be beginner-friendly while still showing professional data engineering and data governance practices: safe configuration handling, modular checks, logging, tests, Docker support, CI, and optional API access.

## Key Features

- Config-driven quality rules in `config/rules.yaml`
- PostgreSQL integration with SQLAlchemy
- Automated checks for completeness, uniqueness, validity, freshness, consistency, and range accuracy
- Failed-row issue details for root cause analysis
- Data lineage metadata for source-table relationships
- Historical SLA tracking for dataset quality targets
- Alert generation and alert resolution from the dashboard
- Streamlit dashboard with filters, charts, run history, profiling, lineage, and exports
- Data profiling for column-level statistics
- Basic anomaly detection plus profile-based drift monitoring with mean, standard deviation, PSI, and category distribution checks
- Quality scoring and severity classification
- CLI shortcuts for common commands
- Optional FastAPI backend
- Optional Apache Airflow DAG for daily orchestration
- Docker Compose setup with PostgreSQL and Streamlit
- Pytest unit tests and GitHub Actions CI

## Tech Stack

| Area | Tools |
|---|---|
| Language | Python |
| Data processing | pandas |
| Database | PostgreSQL |
| Database access | SQLAlchemy, psycopg2 |
| Configuration | YAML, python-dotenv |
| Dashboard | Streamlit, Altair |
| API | FastAPI, Uvicorn |
| Orchestration | Apache Airflow |
| Exports | CSV, Excel, openpyxl |
| Testing | pytest |
| DevOps | Docker, Docker Compose, GitHub Actions |

## Architecture

```text
PostgreSQL source tables
        |
        v
data_sources/postgres_connector.py
        |
        v
config/rules.yaml
config/lineage.yaml
config/sla_rules.yaml
        |
        v
checks/rule_engine.py + checks/anomaly_checks.py + sla/sla_checker.py
        |
        +------------------------------+
        |                              |
        v                              v
reports/generate_report.py       reports/data_profiler.py
        |                              |
        +---------------+--------------+
                        |
                        v
PostgreSQL monitoring tables
        |
        +------------------------------+
        |                              |
        v                              v
dashboard/app.py                 api/app.py
```

## Folder Structure

```text
Automated_Data_Quality_Monotoring_System/
|-- .github/workflows/
|   `-- ci.yml
|-- alerts/
|   `-- alert_manager.py
|-- airflow/
|   `-- dags/
|       `-- data_quality_monitoring_dag.py
|-- api/
|   `-- app.py
|-- checks/
|   |-- anomaly_checks.py
|   |-- drift_detection.py
|   `-- rule_engine.py
|-- config/
|   |-- lineage.yaml
|   |-- rule_loader.py
|   |-- rules.yaml
|   |-- sla_rules.yaml
|   `-- settings.py
|-- dashboard/
|   `-- app.py
|-- data_sources/
|   `-- postgres_connector.py
|-- database/
|   |-- init_db.py
|   `-- seed_sample_data.py
|-- docs/
|   |-- data_governance_framework.md
|   |-- data_quality_rules.md
|   |-- root_cause_analysis_guide.md
|   |-- runbook.md
|   `-- system_architecture.md
|-- notifications/
|-- lineage/
|   |-- lineage_loader.py
|   `-- lineage_service.py
|-- reports/
|   |-- data_profiler.py
|   |-- generate_report.py
|   `-- quality_score.py
|-- sla/
|   `-- sla_checker.py
|-- tests/
|-- cli.py
|-- docker-compose.airflow.yml
|-- docker-compose.yml
|-- Dockerfile
|-- main.py
|-- README.md
|-- requirements-airflow.txt
`-- requirements.txt
```

## Setup On Windows PowerShell

Create and activate a virtual environment:

```powershell
python -m venv .venv
.venv\Scripts\activate
```

Install dependencies:

```powershell
pip install -r requirements.txt
```

Create your local environment file:

```powershell
Copy-Item .env.example .env
```

Update `.env` with your PostgreSQL credentials. Required values are:

```env
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=localhost
DB_PORT=5432
DB_NAME=data_quality_db
```

Do not commit `.env`; it is intentionally listed in `.gitignore`.

## Database Initialization

Create the monitoring tables:

```powershell
python database/init_db.py
```

Create sample source tables and intentionally imperfect data:

```powershell
python database/seed_sample_data.py
```

The sample script creates:

- `customers`
- `orders`
- `products`

It includes examples such as null email, invalid email format, duplicate email, invalid `customer_id`, future order date, negative amount, invalid status, negative price, negative stock, and stale timestamps.

## Run The Project

Run data quality checks:

```powershell
python main.py
```

Run the dashboard:

```powershell
python -m streamlit run dashboard/app.py
```

Run unit tests:

```powershell
pytest tests/
```

## CLI Usage

```powershell
python cli.py init-db
python cli.py run-checks
python cli.py run-dashboard
python cli.py show-latest-run
```

`run-dashboard` prints the Streamlit command so users do not accidentally run the dashboard with plain Python.

## Docker Usage

Start PostgreSQL and the Streamlit dashboard:

```powershell
docker compose up --build
```

Open the dashboard at:

```text
http://localhost:8501
```

Useful Docker commands:

```powershell
docker compose exec dashboard python database/init_db.py
docker compose exec dashboard python database/seed_sample_data.py
docker compose exec dashboard python main.py
docker compose down
```

## Optional Apache Airflow Orchestration

Airflow support is optional and does not change the normal local workflow. The DAG is defined in:

```text
airflow/dags/data_quality_monitoring_dag.py
```

The DAG runs daily by default and orchestrates these tasks:

- `initialize_database`
- `seed_sample_data`
- `run_data_quality_checks`
- `send_notifications`

`run_data_quality_checks` calls `python main.py`, so `main.py` remains the single source of truth for running checks and sending project notifications.

Install Airflow dependencies only when needed:

```powershell
pip install -r requirements-airflow.txt
```

Run Airflow locally with Docker Compose:

```powershell
docker compose -f docker-compose.airflow.yml up --build
```

Open the Airflow UI:

```text
http://localhost:8080
```

Default local credentials come from `.env`:

```env
AIRFLOW_ADMIN_USERNAME=admin
AIRFLOW_ADMIN_PASSWORD=admin
```

To trigger the DAG:

1. Open Airflow at `http://localhost:8080`.
2. Find `data_quality_monitoring`.
3. Toggle the DAG on if it is paused.
4. Click the manual trigger button.

Scheduling:

- The DAG uses `schedule="@daily"`.
- `catchup=False`, so Airflow does not backfill missed historical runs by default.
- Set `DQ_SEED_SAMPLE_DATA=true` if you want the optional seed task to reset sample data during DAG runs.

Stop Airflow:

```powershell
docker compose -f docker-compose.airflow.yml down
```

## Optional FastAPI Backend

Run the API:

```powershell
uvicorn api.app:app --reload
```

Open API docs:

```text
http://127.0.0.1:8000/docs
```

Endpoints include:

- `GET /health`
- `GET /runs`
- `GET /runs/latest`
- `GET /results`
- `GET /results/{run_id}`
- `GET /issues/{run_id}`
- `GET /alerts`
- `PATCH /alerts/{alert_id}/resolve`

## Example Rules

Rules are configured in `config/rules.yaml`.

```yaml
orders:
  required_columns:
    - order_id
    - customer_id
    - order_date
    - amount
    - status

  range_checks:
    amount:
      min: 0
      max: 1000000
    order_date:
      max_date: today

  categorical_checks:
    status:
      allowed_values:
        - pending
        - processing
        - shipped
        - delivered
        - cancelled
        - refunded

  referential_integrity:
    customer_id:
      foreign_table: customers
      foreign_column: customer_id
```

Supported rule types:

- `required_columns`
- `not_null_columns`
- `unique_columns`
- `format_checks`
- `range_checks`
- `categorical_checks`
- `freshness`
- `referential_integrity`
- `custom_rules.email_domains`
- `global_rules.anomaly_detection`
- `global_rules.data_drift_detection`

Example drift configuration:

```yaml
global_rules:
  data_drift_detection:
    enabled: true
    baseline_runs: 3
    mean_change_threshold_percent: 25
    std_change_threshold_percent: 30
    psi_threshold: 0.2
```

## SLA Tracking

Dataset service-level agreements are configured in `config/sla_rules.yaml`.

```yaml
customers:
  minimum_quality_score: 95
  max_critical_issues: 0
  max_failed_checks: 2
  freshness_hours: 24
```

After each run, `main.py` evaluates SLA compliance from the final check results, including anomaly and drift checks. Results are saved to `data_quality_sla_results`.

The dashboard includes an `SLA Tracking` page showing:

- latest SLA status by dataset
- SLA pass-rate trend over runs
- historical SLA violations with reasons

## Data Lineage

Lineage relationships are configured in `config/lineage.yaml`.

```yaml
customers:
  description: Customer master table
  primary_key: customer_id
  downstream:
    - table: orders
      relationship: customers.customer_id -> orders.customer_id
      relationship_type: foreign_key

orders:
  description: Customer order table
  upstream:
    - table: customers
      relationship: orders.customer_id -> customers.customer_id
      relationship_type: foreign_key
```

The dashboard includes a `Data Lineage` page showing:

- source-to-target relationships
- upstream and downstream dependencies
- a lightweight lineage matrix
- failed referential integrity checks mapped to lineage relationships

## Dashboard

Dashboard sections:

- Overview
- Check Results
- Issue Details
- Alerts
- Data Profiling
- Data Lineage
- SLA Tracking
- Run History

Dashboard capabilities:

- Filter by run ID, dataset, status, severity, and alert severity
- View quality score trends
- View failed checks by dataset and check type
- View issue severity distribution
- Track dataset SLA compliance over time
- Resolve alerts
- Export filtered reports to CSV and Excel

## Dashboard Screenshots

```text
docs/screenshots/overview.png
docs/screenshots/overview1.png
docs/screenshots/check-results.png
docs/screenshots/alerts.png
docs/screenshots/screen4.png
docs/screenshots/screen5.png
docs/screenshots/screen6.png
```

## Documentation

- [Data Governance Framework](docs/data_governance_framework.md)
- [Data Quality Rules](docs/data_quality_rules.md)
- [Root Cause Analysis Guide](docs/root_cause_analysis_guide.md)
- [System Architecture](docs/system_architecture.md)
- [Runbook](docs/runbook.md)

## GitHub Actions CI

The workflow in `.github/workflows/ci.yml` runs on push and pull request:

- install dependencies
- run Python syntax checks
- run `pytest tests/`

The tests do not require PostgreSQL.

## Future Improvements

- Add dashboard authentication
- Add Slack or Microsoft Teams alert notifications
- Add role-based alert ownership
- Add cloud warehouse connectors

## CV Bullet Points

- Built a Python data quality monitoring system with PostgreSQL, YAML-driven validation rules, Streamlit dashboards, and automated alerting.
- Implemented modular checks for completeness, uniqueness, validity, freshness, referential integrity, anomaly detection, and drift monitoring.
- Designed monitoring tables for run history, quality scoring, issue details, alerts, and column-level profiling.
- Added Docker Compose, GitHub Actions CI, pytest unit tests, CLI tooling, and optional FastAPI endpoints for portfolio-ready deployment.
