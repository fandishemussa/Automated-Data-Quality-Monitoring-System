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
- Data profiling
- Anomaly and drift checks
- Data lineage
- SLA tracking
- Run history
- CSV and Excel exports

Authentication is controlled by:

```powershell
DASHBOARD_AUTH_ENABLED=true
DASHBOARD_USERNAME=admin
DASHBOARD_PASSWORD=change_me
```

Set `DASHBOARD_AUTH_ENABLED=false` only for local demos.

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
