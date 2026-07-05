# Docker Setup

Create Docker environment values:

```powershell
Copy-Item .env.docker.example .env.docker
```

Start PostgreSQL:

```powershell
docker compose up -d postgres
```

Initialize and run the demo:

```powershell
docker compose run --rm runner python cli.py init-db
docker compose run --rm runner python cli.py seed-demo
docker compose run --rm runner python cli.py run-checks
```

Start the apps:

```powershell
docker compose up -d dashboard api
```

Ports:

- PostgreSQL: `localhost:5433`
- Streamlit: `http://localhost:8501`
- FastAPI: `http://localhost:8000`
