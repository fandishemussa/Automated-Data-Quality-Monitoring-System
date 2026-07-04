def check_outliers_zscore(df, column, threshold=3):
    mean = df[column].mean()
    std = df[column].std()

    if std == 0:
        outlier_count = 0
    else:
        z_scores = (df[column] - mean) / std
        outlier_count = (abs(z_scores) > threshold).sum()

    return {
        "check_type": "outlier_check",
        "column": column,
        "method": "z_score",
        "threshold": threshold,
        "failed_rows": int(outlier_count),
        "status": "PASS" if outlier_count == 0 else "WARNING"
    }