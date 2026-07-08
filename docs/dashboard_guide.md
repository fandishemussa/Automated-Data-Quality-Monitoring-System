# Dashboard Guide

Launch the dashboard:

```powershell
python -m streamlit run dashboard/app.py
```

The dashboard includes:

- Overview metrics
- Check results
- Issue details
- Alerts and alert resolution
- Admin-only Audit Logs
- Data profiling
- Row volume trends and anomaly status
- Rules Catalog for active YAML rule inspection
- Anomaly and drift checks
- Data lineage
- SLA tracking
- Run history
- CSV exports and executive Excel/PDF reports

The Next.js SaaS frontend additionally includes a Data Remediation Center for:

- Cleanable issue triage
- Suggested fixes
- Preview-first cleaning jobs
- Pending approvals
- Change history
- False positives and ignored issues

Roles:

- `admin`: can create, approve, execute, roll back, ignore, resolve, and mark false positives.
- `analyst`: can create jobs and execute approved jobs.
- `data_analyst`: can create jobs and execute approved jobs scoped to assigned issues and alerts.
- `data_engineer`: can create jobs and execute approved jobs without admin-only assignment or approval permissions.
- `viewer`: can view issues only.

Every remediation action is protected by API token authentication and backend role checks. Cleaning jobs never accept arbitrary SQL from the UI; table and column names are validated and updates use parameterized SQLAlchemy statements.

Admin and analyst users can trigger `Run Checks Now` from the Overview or Setup Wizard pages. Viewers can inspect data but cannot trigger checks or export executive reports.

Executive report downloads include:

- Download Excel Report
- Download PDF Executive Summary

If PDF export is unavailable, install the standard requirements so `reportlab` is available:

```powershell
pip install -r requirements.txt
```

Authentication is controlled by:

```powershell
DASHBOARD_AUTH_ENABLED=true
DASHBOARD_USERNAME=admin
DASHBOARD_PASSWORD=change_me
```

Set `DASHBOARD_AUTH_ENABLED=false` only for local demos.

## Next.js User Management

The Next.js console uses database-backed dashboard users. Run the database initializer first:

```powershell
python database/init_db.py
```

When `data_quality_users` is empty, the backend creates the first admin from:

```powershell
DASHBOARD_USERNAME=admin
DASHBOARD_PASSWORD=change_me
```

Sign in at `http://localhost:3000/login`, then open `Administration > User Management` to create analyst and viewer accounts. Supported roles are `admin`, `analyst`, and `viewer`. Admin users can create, activate, and deactivate dashboard users.

## Branding

Set product naming and theme in `.env`:

```powershell
APP_NAME=Automated Data Quality Monitoring System
COMPANY_NAME=Your Company
DASHBOARD_TITLE=Data Quality Command Center
DASHBOARD_ICON=📊
DASHBOARD_THEME=light
```

Place a transparent PNG at `ui/assets/logo.png` or set `BRAND_LOGO_PATH`. If no logo file exists, the dashboard uses a clean `DQ` fallback mark instead of rendering raw shortcode text.

## Audit Logs

Admin users can open `Audit Logs` from the Admin navigation group. The page tracks important operational events such as login, logout, alert edits, alert resolution, report exports, configuration validation, dashboard-triggered checks, API alert reads, API alert resolution, and API authentication failures.

Use the filters for event type, username, entity type, and date range to investigate operational activity. Audit logging is failure-safe: if the audit insert fails, the main dashboard or API action continues and the error is written to the application log.
