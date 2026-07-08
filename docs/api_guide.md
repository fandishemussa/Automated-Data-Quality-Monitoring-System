# API Guide

The FastAPI backend exposes monitoring data for internal tools and automation.

## Run The API

```powershell
uvicorn api.app:app --reload
```

Open interactive docs:

```text
http://127.0.0.1:8000/docs
```

## Authentication

Data endpoints are protected by an API token or a signed dashboard user session when `API_AUTH_ENABLED=true`.

```powershell
API_AUTH_ENABLED=true
API_TOKEN=change_me
API_TOKEN_HEADER=X-API-Key
FRONTEND_URL=http://localhost:3000
```

Send the token in the configured header:

```powershell
Invoke-RestMethod `
  -Uri "http://127.0.0.1:8000/api/v1/runs" `
  -Headers @{"X-API-Key"="change_me"}
```

For local-only demos, set:

```powershell
API_AUTH_ENABLED=false
```

Do not expose the API internally with the default `change_me` token.

The Next.js frontend signs in with username/password through:

```text
POST /api/v1/auth/login
```

The login response includes a signed session token that the frontend sends in `X-API-Key`. When the users table is empty, the first admin is bootstrapped from `DASHBOARD_USERNAME` and `DASHBOARD_PASSWORD`.

## Public Endpoints

- `GET /health`
- `GET /ready`
- `GET /api/v1/health`

`/ready` checks the monitoring database connection and returns `503` when the database is unavailable.

## Versioned Endpoints

- `GET /api/v1/runs`
- `GET /api/v1/runs/latest`
- `GET /api/v1/results`
- `GET /api/v1/results/{run_id}`
- `GET /api/v1/issues/{run_id}`
- `GET /api/v1/alerts`
- `PATCH /api/v1/alerts/{alert_id}/resolve`
- `GET /api/v1/sla`
- `GET /api/v1/lineage`
- `GET /api/v1/profiling`
- `GET /api/v1/rules`
- `GET /api/v1/audit-logs`
- `POST /api/v1/checks/run`
- `POST /api/v1/auth/login`
- `GET /api/v1/users`
- `POST /api/v1/users`
- `PATCH /api/v1/users/{user_id}`
- `DELETE /api/v1/users/{user_id}`

## Remediation Endpoints

Protected remediation endpoints use the same `X-API-Key` header. Write actions also read `X-User` and `X-User-Role` headers so the backend can enforce role permissions.

- `GET /api/v1/issues/cleanable`
- `GET /api/v1/issues/{issue_id}/suggestions`
- `POST /api/v1/cleaning/preview`
- `POST /api/v1/cleaning/jobs`
- `GET /api/v1/cleaning/jobs`
- `GET /api/v1/cleaning/jobs/{job_id}`
- `PATCH /api/v1/cleaning/jobs/{job_id}/approve`
- `POST /api/v1/cleaning/jobs/{job_id}/execute`
- `POST /api/v1/cleaning/jobs/{job_id}/rollback`
- `POST /api/v1/cleaning/jobs/{job_id}/verify`
- `PATCH /api/v1/issues/{issue_id}/status`

Roles:

- `admin`: full remediation permissions.
- `analyst`: create jobs and execute approved jobs.
- `data_analyst`: create jobs and execute approved jobs scoped to assigned issues and alerts.
- `data_engineer`: create jobs and execute approved jobs without admin-only assignment or approval permissions.
- `viewer`: read-only.

Cleaning APIs never accept arbitrary SQL. Source table and column names are validated, dangerous delete operations are not exposed, and all updates are parameterized.

Legacy paths such as `/runs`, `/results`, and `/alerts` are still available temporarily for backward compatibility.

## Pagination

List endpoints support:

- `limit`
- `offset`

Example:

```powershell
Invoke-RestMethod `
  -Uri "http://127.0.0.1:8000/api/v1/results?limit=100&offset=200" `
  -Headers @{"X-API-Key"="change_me"}
```

## Filters

Useful filters include:

- `run_id`
- `dataset_name`
- `severity`
- `status`
- `is_resolved`
- `source_table`
- `target_table`
- `event_type`
- `username`
- `entity_type`

Example:

```powershell
Invoke-RestMethod `
  -Uri "http://127.0.0.1:8000/api/v1/results?run_id=24&dataset_name=orders&status=FAIL" `
  -Headers @{"X-API-Key"="change_me"}
```
