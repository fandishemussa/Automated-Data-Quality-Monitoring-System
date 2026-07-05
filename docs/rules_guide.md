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

Run validation after editing:

```powershell
python cli.py validate-config
```
