# Automated Data Quality Monitoring System

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![PostgreSQL](https://img.shields.io/badge/Database-PostgreSQL-blue)
![Streamlit](https://img.shields.io/badge/Dashboard-Streamlit-red)
![Pandas](https://img.shields.io/badge/Data-Pandas-green)
![Status](https://img.shields.io/badge/Project-Active-success)

## Overview

**Automated Data Quality Monitoring System** is a Python-based data quality and governance project designed to automatically validate datasets, detect data quality issues, store monitoring results, generate alerts, and visualize data health through an interactive Streamlit dashboard.

The system connects to a PostgreSQL database, loads business tables such as `customers`, `orders`, and `products`, applies configurable validation rules from `rules.yaml`, stores check results, captures failed-row examples, and provides a dashboard for monitoring data quality over time.

This project demonstrates practical skills in:

- Data quality monitoring
- Data governance
- PostgreSQL integration
- Python automation
- Rule-based validation
- Root cause analysis
- Alerting
- Dashboard development
- Data documentation

---

## Key Features

### Data Quality Checks

The system supports multiple data quality checks, including:

- Required column validation
- Missing/null value checks
- Duplicate checks
- Format validation
- Range validation
- Categorical value validation
- Freshness checks
- Referential integrity checks
- Custom email domain validation
- Severity classification

---

### Config-Driven Rules

Data quality rules are defined in a YAML configuration file:

```text
config/rules.yaml
```

This makes the system flexible and easy to extend without changing the core Python code.

Example:

```yaml
customers:
  not_null_columns:
    - customer_id
    - name
    - email

  unique_columns:
    - customer_id
    - email

  format_checks:
    email: email

orders:
  range_checks:
    amount:
      min: 0
      max: 1000000

  categorical_checks:
    status:
      allowed_values:
        - pending
        - processing
        - shipped
        - delivered
        - cancelled
```

---

### Run History

Every execution is saved as a separate data quality run.

The system stores:

- Run ID
- Run time
- Total checks
- Passed checks
- Failed checks
- Critical checks
- Quality score
- Overall status

---

### Issue Details

The system does not only count failed checks. It also stores examples of bad rows.

Example issue details:

| Dataset | Check Type | Column | Row Identifier | Bad Value | Reason |
|---|---|---|---|---|---|
| customers | format_check | email | customer_id=3 | wrong-email | email must match format |
| orders | referential_integrity_check | customer_id | order_id=3 | 999 | customer_id must exist in customers.customer_id |

This makes debugging and root cause analysis easier.

---

### Alert System

The system creates alerts when:

- Critical issues are detected
- Failed checks exist
- Quality score falls below threshold

Alerts are saved into PostgreSQL and displayed in the dashboard.

---

### Streamlit Dashboard

The dashboard provides a visual overview of data quality health.

Dashboard sections include:

- Latest run summary
- Quality score trend
- Check results
- Failed checks
- Critical issues
- Issue details / bad row examples
- Alerts
- Issues by severity
- Run history

---

## Tech Stack

| Category | Technology |
|---|---|
| Programming Language | Python |
| Database | PostgreSQL |
| Data Processing | pandas |
| Database Connection | SQLAlchemy, psycopg2 |
| Configuration | YAML, python-dotenv |
| Dashboard | Streamlit |
| Validation Logic | Custom Python Rule Engine |
| Environment | Windows / PowerShell |

---

## System Architecture

```text
PostgreSQL Source Tables
        |
        v
Python Data Loader
        |
        v
rules.yaml Configuration
        |
        v
Data Quality Rule Engine
        |
        v
Quality Results + Issue Details
        |
        v
Alerts + Run History
        |
        v
Streamlit Dashboard
```

---

## Project Structure

```text
Automated_Data_Quality_Monotoring_System/
│
├── alerts/
│   ├── __init__.py
│   └── alert_manager.py
│
├── checks/
│   ├── __init__.py
│   ├── rule_engine.py
│   ├── null_checks.py
│   ├── duplicate_checks.py
│   └── format_checks.py
│
├── config/
│   ├── __init__.py
│   ├── rule_loader.py
│   └── rules.yaml
│
├── dashboard/
│   ├── __init__.py
│   └── app.py
│
├── data_sources/
│   ├── __init__.py
│   └── postgres_connector.py
│
├── docs/
│
├── reports/
│   ├── __init__.py
│   ├── generate_report.py
│   └── quality_score.py
│
├── .env
├── .gitignore
├── main.py
├── requirements.txt
└── README.md
```

---

## Database Tables Used by the System

The system uses the following PostgreSQL tables.

### Source Tables

These tables contain the business data being checked:

```text
customers
orders
products
```

### Monitoring Tables

These tables store data quality monitoring outputs:

```text
data_quality_runs
data_quality_results
data_quality_issue_details
data_quality_alerts
```

---

## Setup Instructions

### 1. Clone the Repository

```powershell
git clone https://github.com/your-username/Automated-Data-Quality-Monitoring-System.git
cd Automated-Data-Quality-Monitoring-System
```

---

### 2. Create Virtual Environment

```powershell
python -m venv .venv
```

Activate it:

```powershell
.venv\Scripts\activate
```

---

### 3. Install Dependencies

```powershell
pip install -r requirements.txt
```

If `requirements.txt` is not complete yet, install the main packages manually:

```powershell
pip install pandas sqlalchemy psycopg2-binary python-dotenv pyyaml streamlit
```

---

## Environment Variables

Create a `.env` file in the project root:

```env
DB_USER=postgres
DB_PASSWORD=your_postgres_password
DB_HOST=localhost
DB_PORT=5432
DB_NAME=data_quality_db
```

Example:

```env
DB_USER=postgres
DB_PASSWORD=your_password_here
DB_HOST=localhost
DB_PORT=5432
DB_NAME=data_quality_db
```

Important:

Do not upload `.env` to GitHub.

Add this to `.gitignore`:

```gitignore
.env
.venv/
__pycache__/
*.pyc
```

---

## PostgreSQL Setup

### Create Database

Open PowerShell and run:

```powershell
psql -U postgres -c "CREATE DATABASE data_quality_db;"
```

---

## Create Sample Source Tables

### Customers Table

```powershell
psql -U postgres -d data_quality_db -c "CREATE TABLE IF NOT EXISTS customers (customer_id SERIAL PRIMARY KEY, name VARCHAR(100), email VARCHAR(100), phone VARCHAR(50), country VARCHAR(50), created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);"
```

Insert sample data:

```powershell
psql -U postgres -d data_quality_db -c "INSERT INTO customers (name, email, phone, country) VALUES ('Ali', 'ali@example.com', '12345', 'Turkey'), ('Sara', NULL, '55555', 'Germany'), ('John', 'wrong-email', '99999', 'USA');"
```

---

### Orders Table

```powershell
psql -U postgres -d data_quality_db -c "CREATE TABLE IF NOT EXISTS orders (order_id SERIAL PRIMARY KEY, customer_id INT, order_date TIMESTAMP, amount NUMERIC(10,2), status VARCHAR(50));"
```

Insert sample data:

```powershell
psql -U postgres -d data_quality_db -c "INSERT INTO orders (customer_id, order_date, amount, status) VALUES (1, CURRENT_TIMESTAMP, 250.00, 'delivered'), (2, CURRENT_TIMESTAMP, 0.00, 'cancelled'), (999, CURRENT_TIMESTAMP, 100.00, 'shipped'), (3, CURRENT_TIMESTAMP + INTERVAL '1 day', 75.00, 'pending'), (1, CURRENT_TIMESTAMP, -20.00, 'unknown_status');"
```

---

### Products Table

```powershell
psql -U postgres -d data_quality_db -c "CREATE TABLE IF NOT EXISTS products (product_id SERIAL PRIMARY KEY, product_name VARCHAR(200), price NUMERIC(10,2), stock INT, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);"
```

Insert sample data:

```powershell
psql -U postgres -d data_quality_db -c "INSERT INTO products (product_name, price, stock, updated_at) VALUES ('Laptop Pro', 1200.00, 15, CURRENT_TIMESTAMP), ('Mouse-USB', 25.00, 5, CURRENT_TIMESTAMP), ('A', 10.00, 20, CURRENT_TIMESTAMP), ('Broken Product', -50.00, 10, CURRENT_TIMESTAMP), ('Old Keyboard', 45.00, -2, CURRENT_TIMESTAMP - INTERVAL '10 days');"
```

---

## Create Monitoring Tables

### Data Quality Runs

```powershell
psql -U postgres -d data_quality_db -c "CREATE TABLE IF NOT EXISTS data_quality_runs (run_id SERIAL PRIMARY KEY, run_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP, total_checks INT, passed_checks INT, failed_checks INT, critical_checks INT, quality_score FLOAT, overall_status VARCHAR(20));"
```

---

### Data Quality Results

```powershell
psql -U postgres -d data_quality_db -c "CREATE TABLE IF NOT EXISTS data_quality_results (id SERIAL PRIMARY KEY, run_id INT, dataset_name VARCHAR(100), check_type VARCHAR(100), column_name VARCHAR(100), rule TEXT, total_rows INT, failed_rows INT, failure_rate FLOAT, status VARCHAR(20), severity VARCHAR(20), run_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP);"
```

---

### Issue Details

```powershell
psql -U postgres -d data_quality_db -c "CREATE TABLE IF NOT EXISTS data_quality_issue_details (id SERIAL PRIMARY KEY, run_id INT, result_id INT, dataset_name VARCHAR(100), check_type VARCHAR(100), column_name VARCHAR(100), row_identifier VARCHAR(255), bad_value TEXT, reason TEXT, sample_row TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);"
```

---

### Alerts

```powershell
psql -U postgres -d data_quality_db -c "CREATE TABLE IF NOT EXISTS data_quality_alerts (id SERIAL PRIMARY KEY, run_id INT, alert_type VARCHAR(100), severity VARCHAR(20), message TEXT, is_resolved BOOLEAN DEFAULT FALSE, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);"
```

---

## How to Run the Data Quality Checks

From the project root, run:

```powershell
python main.py
```

Expected output:

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
```

---

## How to Run the Dashboard

From the project root, run:

```powershell
python -m streamlit run dashboard/app.py
```

The dashboard will open in your browser:

```text
http://localhost:8501
```

---

## Example Dashboard Sections

The Streamlit dashboard includes:

### Latest Run Summary

Shows:

- Run ID
- Quality score
- Total checks
- Passed checks
- Failed checks
- Critical issues
- Alerts

### Quality Score Trend

Shows quality score changes over multiple runs.

### Check Results

Shows all validation results for the selected run.

### Failed Checks

Shows only failed data quality checks.

### Critical Issues

Shows high-priority problems.

### Issue Details

Shows sample failed rows and reasons.

### Alerts

Shows generated alerts for failed or critical checks.

### Run History

Shows all previous data quality runs.

---

## Example Data Quality Results

| Dataset | Check Type | Column | Failed Rows | Status | Severity |
|---|---|---|---:|---|---|
| customers | not_null_check | email | 1 | FAIL | HIGH |
| customers | format_check | email | 1 | FAIL | MEDIUM |
| orders | referential_integrity_check | customer_id | 1 | FAIL | CRITICAL |
| orders | range_check | amount | 1 | FAIL | MEDIUM |
| products | range_check | price | 1 | FAIL | MEDIUM |

---

## Quality Score Logic

The quality score is calculated as:

```text
Quality Score = Passed Checks / Total Checks * 100
```

Example:

```text
Total Checks = 30
Passed Checks = 21

Quality Score = 70%
```

---

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
| required_column_check | CRITICAL |
| referential_integrity_check | CRITICAL |
| not_null_check | HIGH |
| unique_check | HIGH |
| format_check | MEDIUM |
| range_check | MEDIUM |
| freshness_check | MEDIUM |

---

## Data Quality Dimensions Covered

This project covers several important data quality dimensions.

| Dimension | Example |
|---|---|
| Completeness | Required fields should not be null |
| Uniqueness | IDs and emails should be unique |
| Validity | Email should match email format |
| Consistency | Order customer ID should exist in customers table |
| Timeliness | Data should be updated recently |
| Accuracy | Values should be within expected ranges |

---

## Example Rule Configuration

Example from `config/rules.yaml`:

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

---

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

---

## Troubleshooting

### `psql is not recognized`

PostgreSQL is installed, but the PostgreSQL `bin` folder is not added to Windows PATH.

Example path:

```text
C:\Program Files\PostgreSQL\18\bin
```

Add it to Environment Variables → Path.

---

### `password authentication failed`

Check your PostgreSQL username and password in `.env`.

---

### `database does not exist`

Create the database:

```powershell
psql -U postgres -c "CREATE DATABASE data_quality_db;"
```

---

### `ModuleNotFoundError`

Install dependencies:

```powershell
pip install -r requirements.txt
```

Or manually:

```powershell
pip install pandas sqlalchemy psycopg2-binary python-dotenv pyyaml streamlit
```

---

### Streamlit warning: `missing ScriptRunContext`

This happens when running Streamlit with normal Python.

Wrong:

```powershell
python dashboard/app.py
```

Correct:

```powershell
python -m streamlit run dashboard/app.py
```

---

## Requirements

Recommended `requirements.txt`:

```text
pandas
sqlalchemy
psycopg2-binary
python-dotenv
pyyaml
streamlit
```

---

## Future Improvements

Planned improvements:

- Data profiling report
- Data drift detection
- Statistical anomaly detection
- Email notifications
- Alert resolution from dashboard
- Export reports to CSV/Excel
- FastAPI backend
- Docker support
- Unit tests with pytest
- GitHub Actions CI pipeline
- Database initialization script
- Sample data generation script

---

## Portfolio Value

This project is useful for roles such as:

- Data Quality Analyst
- Data Governance Analyst
- Data Engineer
- Analytics Engineer
- Data Analyst
- Data Steward
- Junior Data Platform Engineer

---

## CV / Resume Bullet Points

You can describe this project like this:

```text
Built an automated data quality monitoring system using Python, PostgreSQL, pandas, SQLAlchemy, YAML, and Streamlit. The system extracts data from PostgreSQL, applies configurable validation rules, detects missing values, duplicates, invalid formats, range violations, freshness issues, and referential integrity problems. It stores run history, failed-row issue details, quality scores, severity levels, and alerts in PostgreSQL, and visualizes results through an interactive Streamlit dashboard.
```

Short version:

```text
Developed a Python-based data quality monitoring platform with PostgreSQL integration, YAML-driven validation rules, automated alerting, failed-row issue tracking, quality scoring, and a Streamlit dashboard.
```

---

## Author

**Fandishe Mussa**

Software Engineer and Data Science Enthusiast

---

## License

This project is for educational and portfolio purposes.