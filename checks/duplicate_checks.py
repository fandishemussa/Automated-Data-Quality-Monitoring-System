def check_duplicates(df, column_name):
    total_rows = len(df)
    duplicate_count = df[column_name].duplicated().sum()

    failure_rate = 0
    if total_rows > 0:
        failure_rate = round(float(duplicate_count / total_rows), 4)

    return {
        "check_type": "duplicate_check",
        "column": column_name,
        "total_rows": int(total_rows),
        "failed_rows": int(duplicate_count),
        "failure_rate": failure_rate,
        "status": "PASS" if duplicate_count == 0 else "FAIL"
    }