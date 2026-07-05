from typing import Any


def calculate_quality_score(results: list[dict[str, Any]]) -> float:
    """Calculate the percentage of passing checks, ignoring skipped checks."""

    valid_results = [
        result for result in results
        if result["status"] in ["PASS", "FAIL"]
    ]

    total_checks = len(valid_results)

    if total_checks == 0:
        return 0

    passed_checks = sum(
        1 for result in valid_results
        if result["status"] == "PASS"
    )

    score = (passed_checks / total_checks) * 100

    return round(score, 2)
