from __future__ import annotations

from math import sqrt


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


def wilson_interval(successes: int, total: int, z: float = 1.959963984540054) -> list[float] | None:
    """二項割合の両側95% Wilsonスコア信頼区間。"""
    if total == 0:
        return None
    if not 0 <= successes <= total:
        raise ValueError("successesは0以上total以下である必要があります")
    proportion = successes / total
    denominator = 1 + z * z / total
    center = (proportion + z * z / (2 * total)) / denominator
    margin = z * sqrt(proportion * (1 - proportion) / total + z * z / (4 * total * total)) / denominator
    return [round(max(0.0, center - margin), 6), round(min(1.0, center + margin), 6)]


def rate_with_interval(successes: int, total: int) -> dict[str, int | float | list[float] | None]:
    return {
        "numerator": successes,
        "denominator": total,
        "value": _rate(successes, total),
        "ci95_wilson": wilson_interval(successes, total),
    }


def binary_screening_summary(tp: int, fp: int, fn: int, tn: int) -> dict:
    """陽性対象を1カテゴリとしたスクリーニング指標を返す。"""
    if min(tp, fp, fn, tn) < 0:
        raise ValueError("混同行列の件数は0以上である必要があります")
    total = tp + fp + fn + tn
    sensitivity = _rate(tp, tp + fn)
    specificity = _rate(tn, tn + fp)
    return {
        "confusion_matrix": {"tp": tp, "fp": fp, "fn": fn, "tn": tn, "total": total},
        "sensitivity": rate_with_interval(tp, tp + fn),
        "specificity": rate_with_interval(tn, tn + fp),
        "positive_predictive_value": rate_with_interval(tp, tp + fp),
        "negative_predictive_value": rate_with_interval(tn, tn + fn),
        "accuracy": rate_with_interval(tp + tn, total),
        "f1": {
            "numerator": 2 * tp,
            "denominator": 2 * tp + fp + fn,
            "value": _rate(2 * tp, 2 * tp + fp + fn),
            "ci95_wilson": None,
            "note": "F1は単純な二項割合ではないためWilson区間を付けない。必要時は事例単位bootstrapを用いる。",
        },
        "balanced_accuracy": round((sensitivity + specificity) / 2, 6) if sensitivity is not None and specificity is not None else None,
        "prevalence": rate_with_interval(tp + fn, total),
    }


def summarize(counts: dict[str, int]) -> dict[str, int | float | None]:
    return {
        **counts,
        "precision_vs_silver": _rate(counts["exact"], counts["predicted"]),
        "recall_vs_silver": _rate(counts["exact"], counts["silver_present"]),
        "coverage": _rate(counts["predicted"], counts["total"]),
        "error_rate_among_predictions": _rate(counts["wrong"], counts["predicted"]),
        "abstention_rate": _rate(counts["abstained"], counts["total"]),
    }
