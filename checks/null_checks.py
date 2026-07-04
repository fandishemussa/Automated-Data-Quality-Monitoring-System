def check_missing_values(df, column_name):
    total_rows = len(df)
    missing_count = df[column_name].isnull().sum()

    failure_rate = 0
    if total_rows > 0:
        failure_rate = round(float(missing_count / total_rows), 4)

    return {
        "check_type": "missing_value_check",
        "column": column_name,
        "total_rows": int(total_rows),
        "failed_rows": int(missing_count),
        "failure_rate": failure_rate,
        "status": "PASS" if missing_count == 0 else "FAIL"
    }