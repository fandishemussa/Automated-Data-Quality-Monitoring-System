from reports.quality_score import calculate_quality_score


def test_calculate_quality_score_counts_pass_and_fail_only():
    results = [
        {"status": "PASS"},
        {"status": "PASS"},
        {"status": "FAIL"},
        {"status": "SKIPPED"},
    ]

    assert calculate_quality_score(results) == 66.67


def test_calculate_quality_score_returns_zero_when_no_scored_checks_exist():
    assert calculate_quality_score([{"status": "SKIPPED"}]) == 0
    assert calculate_quality_score([]) == 0
