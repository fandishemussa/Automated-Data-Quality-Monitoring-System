# Automated Data Quality Monitoring System

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![PostgreSQL](https://img.shields.io/badge/Database-PostgreSQL-blue)
![Streamlit](https://img.shields.io/badge/Dashboard-Streamlit-red)
![FastAPI](https://img.shields.io/badge/API-FastAPI-green)
![Docker](https://img.shields.io/badge/Container-Docker-blue)
![Pytest](https://img.shields.io/badge/Tests-Pytest-yellow)
![CI](https://img.shields.io/badge/CI-GitHub%20Actions-black)
![Status](https://img.shields.io/badge/Project-Active-success)

## Overview

**Automated Data Quality Monitoring System** is a production-style Python project for monitoring, validating, profiling, and reporting data quality across database tables.

The system connects to a PostgreSQL database, loads source tables such as `customers`, `orders`, and `products`, applies configurable validation rules from `config/rules.yaml`, stores monitoring results, tracks issue details, generates alerts, sends email notifications, and visualizes data health through an interactive Streamlit dashboard.

It also includes an optional FastAPI backend, Docker support, unit tests, GitHub Actions CI, database initialization scripts, and sample data generation scripts.

This project demonstrates practical skills in:

- Data quality monitoring
- Data governance
- Data profiling
- Data drift detection
- Statistical anomaly detection
- PostgreSQL integration
- Python automation
- YAML-driven validation
- Root cause analysis
- Alerting and email notifications
- Dashboard development
- API development
- Docker-based deployment
- Testing and CI/CD

---

## Key Features

- PostgreSQL data source integration
- Config-driven validation using YAML
- Automated data quality checks
- Required column validation
- Missing/null value checks
- Duplicate checks
- Format validation
- Range validation
- Categorical value validation
- Freshness checks
- Referential integrity validation
- Custom email domain validation
- Failed-row issue tracking
- Data profiling reports
- Data drift detection
- Statistical anomaly detection
- Quality score calculation
- Severity classification
- Alert generation
- Alert resolution from dashboard
- Email notifications using Mailtrap
- Streamlit monitoring dashboard
- CSV/Excel report exports
- Optional FastAPI backend
- Docker support
- Unit tests with pytest
- GitHub Actions CI pipeline
- Database initialization script
- Sample data generation script


## System Architecture

```text
PostgreSQL Source Tables
        |
        v
Python Data Source Connectors
        |
        v
YAML Rules Configuration
        |
        v
Data Quality Rule Engine
        |
        +----------------------------+
        |                            |
        v                            v
Validation Results             Data Profiling
        |                            |
        v                            v
Issue Details                Drift / Anomaly Checks
        |
        v
Run History + Quality Score
        |
        v
Alerts + Email Notifications
        |
        +----------------------------+
        |                            |
        v                            v
Streamlit Dashboard           FastAPI Backend
```


## Data Quality Dimensions Covered

| Dimension | Example |
|---|---|
| Completeness | Required fields should not be null |
| Uniqueness | IDs and emails should be unique |
| Validity | Email should match valid email format |
| Consistency | `orders.customer_id` should exist in `customers.customer_id` |
| Timeliness | Tables should be refreshed within expected time windows |
| Accuracy | Numeric values should stay within valid business ranges |
| Integrity | Foreign-key-like relationships should be valid |
| Reliability | Runs, alerts, and issue details should be stored for review |



## Tech Stack

| Category | Technology |
|---|---|
| Programming Language | Python |
| Database | PostgreSQL |
| Data Processing | pandas |
| Database Connection | SQLAlchemy, psycopg2 |
| Configuration | YAML, python-dotenv |
| Dashboard | Streamlit |
| API | FastAPI, Uvicorn |
| Email Notifications | Mailtrap |
| Exports | CSV, Excel, openpyxl |
| Testing | pytest |
| CI/CD | GitHub Actions |
| Containerization | Docker, Docker Compose |
| Environment | Windows / PowerShell, Linux compatible |



## Project Structure

```text
Automated_Data_Quality_Monitoring_System/
│
├── .github/
│   └── workflows/
│       └── ci.yml
│
├── alerts/
│   ├── __init__.py
│   └── alert_manager.py
│
├── api/
│   ├── __init__.py
│   └── app.py
│
├── checks/
│   ├── __init__.py
│   ├── anomaly_checks.py
│   ├── duplicate_checks.py
│   ├── format_checks.py
│   ├── null_checks.py
│   └── rule_engine.py
│
├── config/
│   ├── __init__.py
│   ├── rule_loader.py
│   ├── rules.yaml
│   └── settings.py
│
├── dashboard/
│   ├── __init__.py
│   └── app.py
│
├── data_sources/
│   ├── __init__.py
│   └── postgres_connector.py
│
├── database/
│   ├── __init__.py
│   ├── init_db.py
│   └── seed_sample_data.py
│
├── docs/
│   ├── data_governance_framework.md
│   ├── data_quality_rules.md
│   ├── root_cause_analysis_guide.md
│   ├── runbook.md
│   └── system_architecture.md
│
├── notifications/
│   ├── __init__.py
│   ├── email_notifier.py
│   └── mailtrap_notifier.py
│
├── reports/
│   ├── __init__.py
│   ├── data_profiler.py
│   ├── generate_report.py
│   └── quality_score.py
│
├── tests/
│   ├── test_rule_engine.py
│   ├── test_quality_score.py
│   └── test_smoke.py
│
├── .env.example
├── .gitignore
├── Dockerfile
├── docker-compose.yml
├── main.py
├── README.md
└── requirements.txt
```

> Some folders or files may vary depending on your current implementation. The structure above represents the recommended professional layout.


## Database Tables

### Source Tables

These are example business/source tables monitored by the system:

```text
customers
orders
products
```

### Monitoring Tables

These tables store system outputs:

```text
data_quality_runs
data_quality_results
data_quality_issue_details
data_quality_alerts
data_profile_results
```


## Monitoring Table Purpose

| Table | Purpose |
|---|---|
| `data_quality_runs` | Stores one row per monitoring execution |
| `data_quality_results` | Stores check-level results for each run |
| `data_quality_issue_details` | Stores sample failed rows and root-cause hints |
| `data_quality_alerts` | Stores alerts generated from failed or critical checks |
| `data_profile_results` | Stores column-level profiling metrics |



## Setup Instructions

### 1. Clone the Repository

```powershell
git clone https://github.com/your-username/Automated-Data-Quality-Monitoring-System.git
cd Automated-Data-Quality-Monitoring-System
```



### 2. Create a Virtual Environment

```powershell
python -m venv .venv
```

Activate it on Windows:

```powershell
.venv\Scripts\activate
```



### 3. Install Dependencies

```powershell
pip install -r requirements.txt
```

If needed, install the main packages manually:

```powershell
pip install pandas sqlalchemy psycopg2-binary python-dotenv pyyaml streamlit pytest fastapi uvicorn mailtrap openpyxl
```



## Environment Variables

Create a `.env` file in the project root.

Example:

```env
# PostgreSQL
DB_USER=postgres
DB_PASSWORD=your_postgres_password
DB_HOST=localhost
DB_PORT=5432
DB_NAME=data_quality_db

# Email Notifications
EMAIL_NOTIFICATIONS_ENABLED=true
EMAIL_PROVIDER=mailtrap

# Mailtrap
MAILTRAP_API_TOKEN=your_mailtrap_api_token
MAILTRAP_SENDER_EMAIL=hello@demomailtrap.co
MAILTRAP_SENDER_NAME=Data Quality Monitor
ALERT_RECIPIENTS=receiver@example.com

# Optional SMTP fallback
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USE_STARTTLS=true
SMTP_USER=your_smtp_user
SMTP_PASSWORD=your_smtp_password
EMAIL_FROM_NAME=Data Quality Monitor
```

Use `.env.example` for safe placeholder values.

Important:

- Do not commit `.env` to GitHub.
- Regenerate any token that was accidentally shared.
- Keep API tokens and database passwords private.

Recommended `.gitignore` entries:

```gitignore
.env
.venv/
__pycache__/
*.pyc
logs/
logs/*.log
.pytest_cache/
*.xlsx
*.csv
```



## PostgreSQL Setup

### Create Database

```powershell
psql -U postgres -c "CREATE DATABASE data_quality_db;"
```

If the database already exists, you can skip this step.



## Initialize Monitoring Tables

If your project includes `database/init_db.py`, run:

```powershell
python database/init_db.py
```

This script should create required monitoring tables such as:

- `data_quality_runs`
- `data_quality_results`
- `data_quality_issue_details`
- `data_quality_alerts`
- `data_profile_results`

If you do not use the script, you can create the tables manually.



## Seed Sample Data

If your project includes `database/seed_sample_data.py`, run:

```powershell
python database/seed_sample_data.py
```

This script should create and populate:

- `customers`
- `orders`
- `products`

The sample data may include intentionally invalid records so that the system can demonstrate failed checks, alerts, and bad-row details.



## Manual Sample Data Setup

### Customers Table

```powershell
psql -U postgres -d data_quality_db -c "CREATE TABLE IF NOT EXISTS customers (customer_id SERIAL PRIMARY KEY, name VARCHAR(100), email VARCHAR(100), phone VARCHAR(50), country VARCHAR(50), created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);"
```

```powershell
psql -U postgres -d data_quality_db -c "INSERT INTO customers (name, email, phone, country) VALUES ('Ali', 'ali@example.com', '12345', 'Turkey'), ('Sara', NULL, '55555', 'Germany'), ('John', 'wrong-email', '99999', 'USA');"
```

### Orders Table

```powershell
psql -U postgres -d data_quality_db -c "CREATE TABLE IF NOT EXISTS orders (order_id SERIAL PRIMARY KEY, customer_id INT, order_date TIMESTAMP, amount NUMERIC(10,2), status VARCHAR(50));"
```

```powershell
psql -U postgres -d data_quality_db -c "INSERT INTO orders (customer_id, order_date, amount, status) VALUES (1, CURRENT_TIMESTAMP, 250.00, 'delivered'), (2, CURRENT_TIMESTAMP, 0.00, 'cancelled'), (999, CURRENT_TIMESTAMP, 100.00, 'shipped'), (3, CURRENT_TIMESTAMP + INTERVAL '1 day', 75.00, 'pending'), (1, CURRENT_TIMESTAMP, -20.00, 'unknown_status');"
```

### Products Table

```powershell
psql -U postgres -d data_quality_db -c "CREATE TABLE IF NOT EXISTS products (product_id SERIAL PRIMARY KEY, product_name VARCHAR(200), price NUMERIC(10,2), stock INT, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);"
```

```powershell
psql -U postgres -d data_quality_db -c "INSERT INTO products (product_name, price, stock, updated_at) VALUES ('Laptop Pro', 1200.00, 15, CURRENT_TIMESTAMP), ('Mouse-USB', 25.00, 5, CURRENT_TIMESTAMP), ('A', 10.00, 20, CURRENT_TIMESTAMP), ('Broken Product', -50.00, 10, CURRENT_TIMESTAMP), ('Old Keyboard', 45.00, -2, CURRENT_TIMESTAMP - INTERVAL '10 days');"
```



## How to Run Data Quality Checks

From the project root:

```powershell
python main.py
```

Example output:

```text
Running checks for table: customers
Running checks for table: orders
Running checks for table: products

--- Summary ---
Total checks: 30
Quality Score: 70.0 %
Overall Status: FAIL

Data quality run saved successfully.
Alerts created.
Email notification sent.
```



## How to Run the Dashboard

```powershell
python -m streamlit run dashboard/app.py
```

The dashboard opens in the browser:

```text
http://localhost:8501
```



## How to Run the FastAPI Backend

If the optional API is implemented, run:

```powershell
uvicorn api.app:app --reload
```

Open:

```text
http://127.0.0.1:8000/docs
```

Example endpoints:

| Method | Endpoint | Description |
|---|---|---|
| GET | `/health` | API health check |
| GET | `/runs` | List quality runs |
| GET | `/runs/latest` | Get latest run |
| GET | `/results` | List quality results |
| GET | `/results/{run_id}` | Get results for a run |
| GET | `/issues/{run_id}` | Get issue details for a run |
| GET | `/alerts` | List alerts |
| PATCH | `/alerts/{alert_id}/resolve` | Resolve an alert |


## Dashboard Sections

The Streamlit dashboard includes:

### Overview

Shows the latest monitoring run summary:

- Run ID
- Quality score
- Total checks
- Passed checks
- Failed checks
- Critical issues
- Open alerts

### Quality Score Trend

Shows how the quality score changes over time.

### Check Results

Shows all checks for the selected run, dataset, status, and severity.

### Failed Checks

Shows failed checks only.

### Critical Issues

Shows high-priority issues that require immediate attention.

### Issue Details

Shows sample failed rows and reasons.

Example:

| Dataset | Check Type | Column | Row Identifier | Bad Value | Reason |
|---|---|---|---|---|---|
| customers | format_check | email | customer_id=3 | wrong-email | email must match format: email |
| orders | referential_integrity_check | customer_id | order_id=3 | 999 | customer_id must exist in customers.customer_id |

### Alerts

Shows generated alerts and allows users to resolve alerts from the dashboard.

### Data Profiling

Shows column-level profiling results such as:

- Data type
- Null count
- Null rate
- Unique count
- Duplicate count
- Min value
- Max value
- Mean value

### Exports

Allows users to export results to:

- CSV
- Excel

### Run History

Shows historical monitoring runs.


## Email Notifications with Mailtrap

The system supports email alert notifications using Mailtrap Email API.

When a data quality run generates alerts, the system automatically sends an email summary containing:

- Run ID
- Overall status
- Quality score
- Total checks
- Passed checks
- Failed checks
- Critical checks
- Alert messages
- Recommended dashboard review action

Example `.env` configuration:

```env
EMAIL_NOTIFICATIONS_ENABLED=true
EMAIL_PROVIDER=mailtrap
MAILTRAP_API_TOKEN=your_mailtrap_token
MAILTRAP_SENDER_EMAIL=hello@demomailtrap.co
MAILTRAP_SENDER_NAME=Data Quality Monitor
ALERT_RECIPIENTS=receiver@example.com
```

Security notes:

- Do not commit Mailtrap API tokens.
- If a token is exposed, revoke/regenerate it immediately.
- Keep `.env` in `.gitignore`.



## Data Quality Rules

Rules are defined in:

```text
config/rules.yaml
```

Example:

```yaml
orders:
  required_columns:
    - order_id
    - customer_id
    - order_date
    - amount
    - status

  not_null_columns:
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



## Supported Rule Types

| Rule Type | Purpose |
|---|---|
| `required_columns` | Ensures required columns exist |
| `not_null_columns` | Ensures fields are not null |
| `unique_columns` | Detects duplicate values |
| `format_checks` | Validates patterns such as email |
| `range_checks` | Validates numeric/date/string ranges |
| `categorical_checks` | Validates allowed values |
| `freshness` | Checks whether data is recently updated |
| `referential_integrity` | Validates table relationships |
| `custom_rules.email_domains` | Validates allowed email domains |
| `global_rules.anomaly_detection` | Enables anomaly detection |
| `global_rules.data_drift_detection` | Enables drift detection |



## Quality Score Logic

The quality score is calculated as:

```text
Quality Score = (Passed Checks / Total Checks) * 100
```

Example:

```text
Total Checks = 30
Passed Checks = 21

Quality Score = 70%
```



## Severity Logic

Each check is assigned a severity level.

| Severity | Meaning |
|---|---|
| NONE | Check passed |
| LOW | Minor issue |
| MEDIUM | Moderate issue |
| HIGH | Serious issue |
| CRITICAL | Critical issue requiring immediate attention |

Examples:

| Check Type | Possible Severity |
|---|---|
| `required_column_check` | CRITICAL |
| `referential_integrity_check` | CRITICAL |
| `not_null_check` | HIGH |
| `unique_check` | HIGH |
| `format_check` | MEDIUM |
| `range_check` | MEDIUM |
| `categorical_check` | MEDIUM |
| `freshness_check` | MEDIUM |
| `anomaly_check` | MEDIUM/HIGH |
| `drift_check` | MEDIUM/HIGH |



## Data Profiling

The data profiling module generates column-level statistics.

Typical metrics include:

| Metric | Description |
|---|---|
| `data_type` | Column data type |
| `total_rows` | Total number of rows |
| `null_count` | Number of missing values |
| `null_rate` | Percentage of missing values |
| `unique_count` | Number of unique values |
| `duplicate_count` | Number of duplicate values |
| `min_value` | Minimum numeric/date value |
| `max_value` | Maximum numeric/date value |
| `mean_value` | Average value for numeric columns |


## Data Drift Detection

The system supports basic drift detection by comparing current profiling/statistical values with historical values from previous runs.

Examples of drift indicators:

- Average value changed significantly
- Numeric distribution shifted
- Null rate increased
- Unique count changed unexpectedly
- Row count changed sharply



## Statistical Anomaly Detection

The system supports statistical anomaly detection for numeric columns.

Example method:

```text
z-score anomaly detection
```

A numeric value may be flagged as anomalous if its absolute z-score exceeds a configured threshold, such as `3`.



## Alerts

Alerts are created when:

- Critical checks exist
- Failed checks exist
- Quality score drops below a threshold
- Drift or anomaly checks detect important issues

Example alerts:

| Alert Type | Severity | Example |
|---|---|---|
| `CRITICAL_DATA_QUALITY_ISSUE` | CRITICAL | Referential integrity failure |
| `DATA_QUALITY_FAILURE` | HIGH | One or more checks failed |
| `LOW_QUALITY_SCORE` | MEDIUM | Quality score below threshold |
| `ANOMALY_DETECTED` | MEDIUM/HIGH | Numeric outliers found |
| `DATA_DRIFT_DETECTED` | MEDIUM/HIGH | Statistical drift detected |



## Exports

The dashboard can export monitoring data for reporting and sharing.

Supported exports:

- Check results as CSV
- Issue details as CSV
- Alerts as CSV
- Run history as CSV
- Excel workbook with multiple sheets

This is useful for sharing reports with product managers, engineering, operations, or governance teams.



## Docker Usage

If Docker support is implemented, run:

```powershell
docker compose up --build
```

Typical services:

| Service | Purpose |
|---|---|
| `postgres` | PostgreSQL database |
| `dashboard` | Streamlit dashboard |
| `api` | Optional FastAPI backend |

Stop containers:

```powershell
docker compose down
```



## Testing

Run tests with:

```powershell
pytest -q
```

Run syntax check:

```powershell
python -m compileall .
```

Example test coverage:

- Project structure smoke tests
- YAML validation
- Rule engine functions
- Quality score calculation
- Severity calculation
- Data validation helpers



## GitHub Actions CI

The project includes a GitHub Actions workflow:

```text
.github/workflows/ci.yml
```

The CI pipeline runs on:

- Push
- Pull request
- Manual workflow dispatch

Typical CI steps:

- Checkout repository
- Set up Python
- Install dependencies
- Run syntax checks
- Run pytest tests



## Useful PostgreSQL Commands

List databases:

```powershell
psql -U postgres -c "\l"
```

Connect to database:

```powershell
psql -U postgres -d data_quality_db
```

List tables:

```sql
\dt
```

View latest run:

```powershell
psql -U postgres -d data_quality_db -c "SELECT * FROM data_quality_runs ORDER BY run_id DESC LIMIT 1;"
```

View latest results:

```powershell
psql -U postgres -d data_quality_db -c "SELECT run_id, dataset_name, check_type, column_name, status, severity FROM data_quality_results ORDER BY id DESC LIMIT 20;"
```

View issue details:

```powershell
psql -U postgres -d data_quality_db -c "SELECT run_id, dataset_name, check_type, column_name, row_identifier, bad_value, reason FROM data_quality_issue_details ORDER BY id DESC LIMIT 20;"
```

View alerts:

```powershell
psql -U postgres -d data_quality_db -c "SELECT id, run_id, alert_type, severity, message, is_resolved FROM data_quality_alerts ORDER BY id DESC LIMIT 20;"
```



## Troubleshooting

### `psql is not recognized`

PostgreSQL is installed, but the PostgreSQL `bin` folder is not added to Windows PATH.

Example path:

```text
C:\Program Files\PostgreSQL\18\bin
```

Add it to:

```text
Environment Variables → Path
```



### `password authentication failed`

Check your `.env` values:

```env
DB_USER=postgres
DB_PASSWORD=your_postgres_password
```



### `database does not exist`

Create the database:

```powershell
psql -U postgres -c "CREATE DATABASE data_quality_db;"
```



### `ModuleNotFoundError`

Install dependencies:

```powershell
pip install -r requirements.txt
```



### Streamlit warning: `missing ScriptRunContext`

Wrong:

```powershell
python dashboard/app.py
```

Correct:

```powershell
python -m streamlit run dashboard/app.py
```



### Email notification fails

Check:

- `EMAIL_NOTIFICATIONS_ENABLED=true`
- `MAILTRAP_API_TOKEN` is valid
- `ALERT_RECIPIENTS` is set
- The sender email is accepted by Mailtrap
- `.env` was saved
- The script was restarted after changing `.env`



## Recommended `requirements.txt`

```text
altair
fastapi
mailtrap
openpyxl
pandas
psycopg2-binary
pytest
python-dotenv
pyyaml
sqlalchemy
streamlit
uvicorn
```

If anomaly detection uses scikit-learn, also include:

```text
scikit-learn
numpy
```



## Portfolio Value

This project is useful for roles such as:

- Data Quality Analyst
- Data Governance Analyst
- Data Engineer
- Analytics Engineer
- Data Analyst
- Data Steward
- Junior Data Platform Engineer
- Data Platform Engineer
- BI Engineer

## Future Enhancements

Although the main system features are implemented, future improvements could include:

- Role-based dashboard access
- User authentication for dashboard and API
- Advanced data lineage tracking
- Integration with cloud warehouses such as Amazon Redshift, Snowflake, or BigQuery
- Integration with orchestration tools such as Apache Airflow
- Slack or Microsoft Teams alert notifications
- More advanced statistical drift detection
- Machine learning-based anomaly detection
- Data quality SLA tracking
- Multi-environment deployment support
- Better audit logs and approval workflows
- More advanced root cause analysis workflows


## Author

**Fandishe Mussa**

Software Engineer and Data Science Enthusiast

