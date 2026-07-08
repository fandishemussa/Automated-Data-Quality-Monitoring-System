# API Reference

## Authentication

Protected endpoints require the API token header when `API_AUTH_ENABLED=true`.

```http
X-API-Key: change_me
```

Dashboard session calls may also include signed user identity headers created by the login flow. Backend permission checks are enforced server-side and do not rely on hidden frontend buttons.

## Remediation Roles

| Role | Permissions |
| --- | --- |
| `admin` | Full remediation access, assignment, approval, execution, rollback, user management |
| `analyst` | View issues, preview cleaning, create jobs, execute approved jobs, update issue lifecycle |
| `data_analyst` | Same as analyst, scoped to alerts/issues assigned to their username |
| `data_engineer` | Create and execute approved remediation jobs, update issue lifecycle, no admin approval/assignment |
| `viewer` | Read-only access |

## Cleaning Job Lifecycle

```text
Open Issue -> Suggested Fix -> Preview -> Create Job -> Approve -> Execute -> Change Log -> Verify -> Resolve
```

Every source-data update must be previewed before job creation. Execution records before/after values in `data_cleaning_change_log` before updating the source table. Rollback is admin-only and fails safely if no change log exists or the job is not in `EXECUTED` status.

## Issue Status Lifecycle

Supported statuses:

- `OPEN`
- `ASSIGNED`
- `IN_REVIEW`
- `FIX_PROPOSED`
- `FIX_APPLIED`
- `FALSE_POSITIVE`
- `IGNORED`
- `RESOLVED`

When an issue is marked `FIX_APPLIED`, `FALSE_POSITIVE`, `IGNORED`, or `RESOLVED`, related open alerts can be automatically resolved when no open issue remains for the dataset/run.

## Remediation Endpoints

### List Cleanable Issues

```http
GET /api/v1/issues/cleanable
```

Optional query parameters:

- `run_id`
- `dataset_name`
- `status`
- `severity`

`data_analyst` users receive only issues assigned to their username.

### Get Suggestions

```http
GET /api/v1/issues/{issue_id}/suggestions
```

Returns suggested safe cleaning actions for one issue.

### Preview Cleaning

```http
POST /api/v1/cleaning/preview
Content-Type: application/json

{
  "issue_id": 123,
  "action": "replace_value",
  "target_table": "customers",
  "target_column": "email",
  "row_identifier": "customer_id=42",
  "new_value": "customer@example.com"
}
```

Returns targeted rows and proposed before/after values. No source data is changed.

### Create Cleaning Job

```http
POST /api/v1/cleaning/jobs
```

Creates a job from a previewable payload. Policy in `config/data_cleaning_policy.yaml` controls whether approval is required, which actions are allowed, and max rows per job.

### List Cleaning Jobs

```http
GET /api/v1/cleaning/jobs
```

Optional query parameters:

- `status`
- `dataset_name`
- `requested_by`

`data_analyst` users receive jobs tied to assigned issues or jobs requested by them.

### Approve Job

```http
PATCH /api/v1/cleaning/jobs/{job_id}/approve
```

Admin-only.

### Execute Job

```http
POST /api/v1/cleaning/jobs/{job_id}/execute
```

Allowed for admin and for analyst/data analyst/data engineer roles when the job is approved or ready for execution. Source updates are blocked when `allow_source_updates=false`.

### Rollback Job

```http
POST /api/v1/cleaning/jobs/{job_id}/rollback
```

Admin-only. Requires an executed job and existing change log records.

### Verify Job

```http
POST /api/v1/cleaning/jobs/{job_id}/verify
```

Records verification intent. Operators should rerun checks and compare latest issue results.

### Update Issue Status

```http
PATCH /api/v1/issues/{issue_id}/status
Content-Type: application/json

{
  "status": "RESOLVED",
  "notes": "Validated after rerun."
}
```

Assignment uses `status=ASSIGNED` and is admin-only.

## Alert Endpoints

```http
GET /api/v1/alerts
PATCH /api/v1/alerts/{alert_id}/acknowledge
PATCH /api/v1/alerts/{alert_id}/assign
PATCH /api/v1/alerts/{alert_id}/escalate
PATCH /api/v1/alerts/{alert_id}/resolve
```

Viewers cannot mutate alerts. `data_analyst` users only see and mutate alerts assigned to their username. Alert assignment is admin-only.
