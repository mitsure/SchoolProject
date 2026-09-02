from __future__ import annotations


def empty_counts() -> dict[str, int]:
    return {"total": 0, "predicted": 0, "silver_present": 0, "exact": 0, "wrong": 0, "abstained": 0}


def update_counts(counts: dict[str, int], predicted: str | None, silver: str | None) -> None:
    counts["total"] += 1
    if predicted is not None:
        counts["predicted"] += 1
    else:
        counts["abstained"] += 1
    if silver is not None:
        counts["silver_present"] += 1
    if predicted is not None and predicted == silver:
        counts["exact"] += 1
    elif predicted is not None:
        counts["wrong"] += 1


def _rate(numerator: int, denominator: int) -> float | None:
    return round(numerator / denominator, 6) if denominator else None


def summarize(counts: dict[str, int]) -> dict[str, int | float | None]:
    return {
        **counts,
        "precision_vs_silver": _rate(counts["exact"], counts["predicted"]),
        "recall_vs_silver": _rate(counts["exact"], counts["silver_present"]),
        "coverage": _rate(counts["predicted"], counts["total"]),
        "error_rate_among_predictions": _rate(counts["wrong"], counts["predicted"]),
        "abstention_rate": _rate(counts["abstained"], counts["total"]),
    }
