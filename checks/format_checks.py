def check_email_format(df, column_name):
    pattern = r"^[\w\.-]+@[\w\.-]+\.\w+$"

    non_null_df = df[df[column_name].notnull()]
    invalid_rows = non_null_df[
        ~non_null_df[column_name].str.contains(pattern, regex=True)
    ]

    total_rows = len(df)
    invalid_count = len(invalid_rows)

    failure_rate = 0
    if total_rows > 0:
        failure_rate = round(float(invalid_count / total_rows), 4)

    return {
        "check_type": "format_check",
        "column": column_name,
        "rule": "valid_email",
        "total_rows": int(total_rows),
        "failed_rows": int(invalid_count),
        "failure_rate": failure_rate,
        "status": "PASS" if invalid_count == 0 else "FAIL"
    }