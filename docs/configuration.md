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

## Data Cleaning Safety Policy

Data remediation is controlled by:

```text
config/data_cleaning_policy.yaml
```

Important settings:

- `enabled`: turns remediation features on or off.
- `allow_source_updates`: must be true before execution can update source data.
- `allow_delete_rows`: should remain false; dashboard delete operations are not implemented.
- `max_rows_per_job`: limits blast radius per cleaning job.
- `allowed_actions`: cleaning actions that can be previewed or proposed.
- `restricted_actions`: actions blocked by policy.
- `high_risk_actions`: actions that should require approval.
- `role_policy`: controls whether a role can execute without approval.

Recommended production posture:

- Require approval for high-risk jobs.
- Use staging first.
- Ensure source database credentials have limited write scope.
- Keep backups and point-in-time recovery enabled.

## Source Connectors

The canonical source connector architecture lives in `data_sources/`.
`connectors/` remains as a backward-compatible wrapper package for older imports.

```powershell
SOURCE_DB_TYPE=postgres
```

Supported values:

- `postgres`
- `redshift`
- `snowflake`
- `bigquery`
- `mongodb`

PostgreSQL remains the default and does not require optional cloud dependencies.

### Redshift

```powershell
SOURCE_DB_TYPE=redshift
REDSHIFT_HOST=your-redshift-cluster.amazonaws.com
REDSHIFT_PORT=5439
REDSHIFT_DB=analytics
REDSHIFT_USER=redshift_user
REDSHIFT_PASSWORD=redshift_password
REDSHIFT_SCHEMA=public
```

### Snowflake

Install optional dependencies:

```powershell
pip install -r requirements-snowflake.txt
```

Then configure:

```powershell
SOURCE_DB_TYPE=snowflake
SNOWFLAKE_ACCOUNT=your_account
SNOWFLAKE_USER=your_user
SNOWFLAKE_PASSWORD=your_password
SNOWFLAKE_WAREHOUSE=your_warehouse
SNOWFLAKE_DATABASE=your_database
SNOWFLAKE_SCHEMA=PUBLIC
```

### BigQuery

Install optional dependencies:

```powershell
pip install -r requirements-bigquery.txt
```

Then configure:

```powershell
SOURCE_DB_TYPE=bigquery
GOOGLE_APPLICATION_CREDENTIALS=C:\path\to\service-account.json
BIGQUERY_PROJECT_ID=your_project_id
BIGQUERY_DATASET=your_dataset
```

### MongoDB

MongoDB support is scaffolded as an optional connector:

```powershell
SOURCE_DB_TYPE=mongodb
MONGODB_URI=mongodb://localhost:27017
MONGODB_DATABASE=analytics
```

## Preflight

`main.py` runs configuration preflight checks before saving results. To skip in a special environment:

```powershell
SKIP_PREFLIGHT_CHECK=true
```

Normal users should leave this as `false`.
