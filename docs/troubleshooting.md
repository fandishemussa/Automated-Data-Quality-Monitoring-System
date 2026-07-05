# Troubleshooting

## Validate First

```powershell
python cli.py validate-config
```

Common fixes:

- Missing monitoring tables: `python cli.py init-db`
- Missing demo source tables: `python cli.py seed-demo`
- Dashboard login not showing: set `DASHBOARD_AUTH_ENABLED=true` and restart Streamlit
- Docker cannot find env file: `Copy-Item .env.docker.example .env.docker`

## PostgreSQL Port Conflict

Docker maps PostgreSQL to host port `5433`. Connect local tools to `localhost:5433` for the container database.

## Optional Connector Errors

Install optional connector dependencies only when needed:

```powershell
pip install -r requirements-snowflake.txt
pip install -r requirements-bigquery.txt
```
