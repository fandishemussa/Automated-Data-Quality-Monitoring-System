import pandas as pd

def check_freshness(df, date_column, max_delay_days):
    latest_date = pd.to_datetime(df[date_column]).max()
    today = pd.Timestamp.now()
    delay_days = (today - latest_date).days

    return {
        "check_type": "freshness_check",
        "column": date_column,
        "latest_date": str(latest_date),
        "delay_days": delay_days,
        "status": "PASS" if delay_days <= max_delay_days else "FAIL"
    }