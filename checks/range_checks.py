def check_range(df, column, min_value=None, max_value=None):
    failed = df.copy()

    if min_value is not None:
        failed = failed[failed[column] < min_value]

    if max_value is not None:
        failed = failed[failed[column] > max_value]

    return {
        "check_type": "range_check",
        "column": column,
        "min_value": min_value,
        "max_value": max_value,
        "failed_rows": len(failed),
        "status": "PASS" if len(failed) == 0 else "FAIL"
    }