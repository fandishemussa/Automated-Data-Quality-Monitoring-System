# Installation

## Requirements

- Python 3.10+
- PostgreSQL 13+
- Windows PowerShell, Windows Terminal, or a compatible shell

## Local Install

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
Copy-Item config\rules.example.yaml config\rules.yaml
```

Edit `.env`, then validate the setup:

```powershell
python cli.py validate-config
```

## Optional Packages

```powershell
pip install -r requirements-airflow.txt
pip install -r requirements-snowflake.txt
pip install -r requirements-bigquery.txt
```

Install optional connector packages only when you need those integrations.
