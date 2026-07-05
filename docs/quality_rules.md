# Quality Rules

The current rule reference lives in [data_quality_rules.md](data_quality_rules.md).

Use this shorter page as a quick checklist when reviewing or extending `config/rules.yaml`.

## Checklist

- Required columns are listed for every monitored table.
- Business-critical fields are included in `not_null_columns`.
- Primary identifiers are included in `unique_columns`.
- Email and name-like fields use `format_checks` where appropriate.
- Numeric fields have sensible minimum and maximum values.
- Date fields prevent future values when required.
- Categorical fields list all accepted values.
- Relationship fields use `referential_integrity`.
- Freshness checks reflect business expectations.
- Global anomaly and drift settings are enabled only when useful historical data exists.
