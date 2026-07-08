# Rules Guide

Rules live in `config/rules.yaml`. Start from:

```powershell
Copy-Item config\rules.example.yaml config\rules.yaml
```

Supported rule sections include:

- `required_columns`
- `not_null_columns`
- `unique_columns`
- `format_checks`
- `range_checks`
- `categorical_checks`
- `freshness`
- `referential_integrity`
- `custom_rules.email_domains`
- `global_rules`
- `quality_thresholds`

## Rules Catalog

The Streamlit dashboard includes a read-only `Rules Catalog` page under Governance. It flattens `config/rules.yaml` into searchable rows with dataset, rule type, column, rule configuration, severity, and enabled status.

Use the page to:

- inspect active YAML rules without opening files
- filter by dataset, rule type, and column
- search rule configuration text
- export the current catalog view as CSV
- view the raw YAML in a safe read-only expander

Rule editing and approval workflow is intentionally disabled for now and listed as a Pro/Enterprise roadmap feature.

## Schema Drift Detection

Schema drift detection compares the current source table schema with the latest saved schema snapshot in PostgreSQL.

```yaml
global_rules:
  schema_drift_detection:
    enabled: true
    severity: HIGH
```

On the first run, the system saves a baseline snapshot and returns a skipped baseline result. Later runs detect:

- added columns
- removed columns
- changed data types
- changed nullability
- changed column order

Schema drift results are saved as `schema_drift_check` rows and appear in the dashboard Check Results page.

## Row Volume Anomaly Detection

Row volume anomaly detection compares each dataset's current row count with recent historical row counts saved in PostgreSQL.

```yaml
global_rules:
  volume_anomaly_detection:
    enabled: true
    baseline_runs: 5
    change_threshold_percent: 40
    severity: HIGH
```

On the first run, the system saves the current row count as a baseline and returns a skipped baseline result. Later runs detect both drops and spikes by comparing the signed percent change against the absolute threshold. Results are saved as `row_volume_anomaly_check` rows and history is stored in `data_volume_history`.

Run validation after editing:

```powershell
python cli.py validate-config
```
