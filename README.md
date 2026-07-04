# Automated-Data-Quality-Monitoring-System
An automated data quality monitoring system that validates datasets, detects quality issues, stores results, and visualizes key metrics through an interactive dashboard.

## Database Initialization

Create the required PostgreSQL monitoring tables before running checks:

```powershell
python database/init_db.py
```

The initialization script is safe to run multiple times.

Running `python main.py` stores both data quality results and column-level data profiling results for each monitored dataset.

The run also includes statistical z-score anomaly checks and mean-based drift checks when they are enabled in `config/rules.yaml`.
