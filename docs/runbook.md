# Runbook

This runbook explains how to operate and troubleshoot the project during local development or portfolio demos.

## Prerequisites

- Python 3.10 or newer
- PostgreSQL
- Optional: Docker Desktop

## Local Setup

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Create `.env` from `.env.example` and update the PostgreSQL values.

## Initialize The Database

```powershell
python database/init_db.py
```

This creates the monitoring tables used by the reports, dashboard, and API.

## Seed Sample Data

```powershell
python database/seed_sample_data.py
```

This resets and populates `customers`, `orders`, and `products` with a mix of valid and intentionally invalid rows.

## Run Checks

```powershell
python main.py
```

or:

```powershell
python cli.py run-checks
```

## Run The Dashboard

```powershell
python -m streamlit run dashboard/app.py
```

Open `http://localhost:8501`.

## Run The API

```powershell
uvicorn api.app:app --reload
```

Open `http://127.0.0.1:8000/docs`.

## Docker

```powershell
docker compose up --build
```

Then initialize and seed data inside the dashboard container if needed:

```powershell
docker compose exec dashboard python database/init_db.py
docker compose exec dashboard python database/seed_sample_data.py
docker compose exec dashboard python main.py
```

## Tests

```powershell
pytest tests/
```

Tests use small pandas DataFrames and do not require PostgreSQL.

## Common Issues

### Missing Environment Variables

Symptom:

```text
Missing required database environment variable(s)
```

Fix:

- Create `.env` in the project root.
- Copy values from `.env.example`.
- Confirm `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`, and `DB_NAME`.

### Database Connection Fails

Fix:

- Confirm PostgreSQL is running.
- Confirm `DB_HOST` is `localhost` for local runs.
- Confirm `DB_HOST` is `postgres` inside Docker Compose.
- Confirm the database exists.

### Monitoring Tables Missing

Fix:

```powershell
python database/init_db.py
```

### No Source Tables Found

Fix:

```powershell
python database/seed_sample_data.py
```

or create your own `customers`, `orders`, and `products` tables that match `config/rules.yaml`.

### Streamlit Context Warning

Run the dashboard with Streamlit, not plain Python:

```powershell
python -m streamlit run dashboard/app.py
```

### Email Notifications Not Sending

Fix:

- Set `EMAIL_NOTIFICATIONS_ENABLED=true`.
- Configure Mailtrap or SMTP variables.
- Confirm `ALERT_RECIPIENTS` is set.
- Check `logs/app.log`.

## Operational Checklist

Before a demo:

- `.env` exists and uses safe local credentials.
- `python database/init_db.py` succeeds.
- `python database/seed_sample_data.py` succeeds.
- `python main.py` creates a run.
- `python -m streamlit run dashboard/app.py` opens.
- `pytest tests/` passes.
