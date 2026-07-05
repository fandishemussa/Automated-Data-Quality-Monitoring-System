# Quickstart

## Local Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
Copy-Item config\rules.example.yaml config\rules.yaml
```

Edit `.env` with your PostgreSQL values. For a simple local demo, keep `SOURCE_DB_*`, `MONITOR_DB_*`, and legacy `DB_*` pointed at the same database.

## Prepare The Database

```powershell
python cli.py validate-config
python cli.py init-db
python cli.py seed-demo
python cli.py run-checks
```

If validation reports missing monitoring tables, run `python cli.py init-db` again. The initializer is safe to run multiple times.

## Launch Apps

```powershell
python -m streamlit run dashboard/app.py
uvicorn api.app:app --reload
```

The dashboard opens on `http://localhost:8501`. The API opens on `http://127.0.0.1:8000`.

## Docker Setup

```powershell
Copy-Item .env.docker.example .env.docker
docker compose up -d postgres
docker compose run --rm runner python cli.py init-db
docker compose run --rm runner python cli.py seed-demo
docker compose run --rm runner python cli.py run-checks
docker compose up -d dashboard api
```

Docker exposes PostgreSQL on host port `5433`, Streamlit on `8501`, and FastAPI on `8000`.

## Release Checks

```powershell
python cli.py release-audit
python cli.py build-release
```

The release archive is written to `release/` and excludes secrets, logs, bytecode, virtual environments, and local junk files.
