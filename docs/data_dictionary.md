# Data Dictionary

This project uses two categories of tables: source tables that are monitored and monitoring tables that store system output.

## Sample Source Tables

### customers

| Column | Description |
|---|---|
| `customer_id` | Unique customer identifier. |
| `name` | Customer name. |
| `email` | Customer email address. |
| `created_at` | Customer creation timestamp. |

### orders

| Column | Description |
|---|---|
| `order_id` | Unique order identifier. |
| `customer_id` | Customer linked to the order. |
| `order_date` | Order timestamp. |
| `amount` | Order amount. |
| `status` | Order lifecycle status. |

### products

| Column | Description |
|---|---|
| `product_id` | Unique product identifier. |
| `product_name` | Product display name. |
| `price` | Product price. |
| `stock` | Available stock count. |
| `updated_at` | Last product update timestamp. |

## Monitoring Tables

| Table | Purpose |
|---|---|
| `data_quality_runs` | One row per monitoring execution. |
| `data_quality_results` | One row per quality check result. |
| `data_quality_issue_details` | Sample failed rows and root-cause context. |
| `data_quality_alerts` | Alerts generated from failed or critical checks. |
| `data_profile_results` | Column-level profiling statistics. |
| `data_quality_sla_results` | Dataset SLA status, actual metrics, thresholds, and violation reasons per run. |
| `data_lineage_edges` | Optional persisted source-to-target lineage relationships. |
