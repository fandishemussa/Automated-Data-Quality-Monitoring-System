# Data Quality Rules

Rules live in `config/rules.yaml`. Each top-level dataset section should match a PostgreSQL source table name, such as `customers`, `orders`, or `products`.

## Rule Types

| Rule | Purpose | Example |
|---|---|---|
| `required_columns` | Confirms required columns exist. | `customer_id`, `email` |
| `not_null_columns` | Finds missing values in important fields. | `email must not be null` |
| `unique_columns` | Finds duplicate values. | `customer_id`, `email` |
| `format_checks` | Validates named patterns. | `email: email` |
| `range_checks` | Validates numeric, length, and date constraints. | `amount.min: 0` |
| `categorical_checks` | Validates values against an allowed list. | order status values |
| `freshness` | Checks whether timestamps are recent enough. | `max_delay_days: 1` |
| `referential_integrity` | Checks values against another table. | `orders.customer_id` exists in `customers.customer_id` |
| `custom_rules.email_domains` | Allows only configured email domains. | `gmail.com`, `company.com` |
| `global_rules.anomaly_detection` | Runs numeric z-score anomaly checks. | absolute z-score above 3 |
| `global_rules.data_drift_detection` | Compares current profiles to historical profiles. | mean, standard deviation, PSI, category distribution |

## Example

```yaml
orders:
  required_columns:
    - order_id
    - customer_id
    - order_date
    - amount
    - status

  not_null_columns:
    - order_id
    - customer_id
    - amount

  range_checks:
    amount:
      min: 0
      max: 1000000
    order_date:
      max_date: today

  categorical_checks:
    status:
      allowed_values:
        - pending
        - processing
        - shipped
        - delivered
        - cancelled
        - refunded

  referential_integrity:
    customer_id:
      foreign_table: customers
      foreign_column: customer_id
```

## Drift Configuration

```yaml
global_rules:
  data_drift_detection:
    enabled: true
    baseline_runs: 3
    mean_change_threshold_percent: 25
    std_change_threshold_percent: 30
    psi_threshold: 0.2
```

The drift checker uses previous rows from `data_profile_results` as the baseline. If no history exists, it returns a skipped result instead of failing the run.

## Result Fields

Every rule returns a standardized result dictionary:

- `dataset_name`
- `check_type`
- `column`
- `rule`
- `total_rows`
- `failed_rows`
- `failure_rate`
- `status`
- `severity`
- `details`

This structure lets the reporting, alerting, dashboard, and API layers consume results consistently.

## Severity Guidance

| Severity | Typical Meaning |
|---|---|
| `NONE` | The check passed. |
| `LOW` | Small or informational issue. |
| `MEDIUM` | Issue should be reviewed. |
| `HIGH` | Serious issue affecting trust in the dataset. |
| `CRITICAL` | Missing required structure or major integrity failure. |
