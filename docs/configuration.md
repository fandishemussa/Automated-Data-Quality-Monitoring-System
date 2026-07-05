# Configuration

The project loads environment variables from `.env` using `python-dotenv`.

## Database Settings

Legacy `DB_*` variables remain supported:

```powershell
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=localhost
DB_PORT=5432
DB_NAME=data_quality_db
```

For production-style separation, use:

```powershell
SOURCE_DB_USER=postgres
SOURCE_DB_PASSWORD=postgres
SOURCE_DB_HOST=localhost
SOURCE_DB_PORT=5432
SOURCE_DB_NAME=data_quality_db

MONITOR_DB_USER=postgres
MONITOR_DB_PASSWORD=postgres
MONITOR_DB_HOST=localhost
MONITOR_DB_PORT=5432
MONITOR_DB_NAME=data_quality_db
```

If `SOURCE_DB_*` or `MONITOR_DB_*` are missing, the app falls back to `DB_*`.

## Preflight

`main.py` runs configuration preflight checks before saving results. To skip in a special environment:

```powershell
SKIP_PREFLIGHT_CHECK=true
```

Normal users should leave this as `false`.
