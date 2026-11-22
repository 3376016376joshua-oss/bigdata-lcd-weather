"""Pure-Python binary classification metrics derived from confusion counts."""

from __future__ import annotations

from collections.abc import Mapping

DEFAULT_THRESHOLD = 0.5
CURVE_BINS = 100


def _ratio(numerator: float, denominator: float) -> float | None:
    return numerator / denominator if denominator else None


def derive_binary_metrics(tp: int, fp: int, tn: int, fn: int) -> dict[str, float | None]:
    """Precision, recall, F1, accuracy and false-positive rate (None if undefined)."""
    precision = _ratio(tp, tp + fp)
    recall = _ratio(tp, tp + fn)
    f1 = None
    if precision is not None and recall is not None:
        f1 = _ratio(2 * precision * recall, precision + recall)
    return {
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "accuracy": _ratio(tp + tn, tp + fp + tn + fn),
        "fpr": _ratio(fp, fp + tn),
    }


def curve_from_histogram(
    histogram: Mapping[int, tuple[int, int]], n_bins: int = CURVE_BINS
) -> list[dict]:
    """Confusion counts at thresholds 0, 1/n, ..., 1 from per-bin (positives, total).

    A score falls in bin floor(score * n_bins) (capped at n_bins - 1) and is
    predicted positive at threshold i / n_bins when its bin is >= i.
    """
    total_positives = sum(positives for positives, _ in histogram.values())
    total = sum(count for _, count in histogram.values())
    total_negatives = total - total_positives
    curve = []
    tp = 0
    fp = 0
    for index in range(n_bins, -1, -1):
        positives, count = histogram.get(index, (0, 0))
        tp += positives
        fp += count - positives
        point = {
            "threshold": index / n_bins,
            "tp": tp,
            "fp": fp,
            "tn": total_negatives - fp,
            "fn": total_positives - tp,
        }
        point.update(derive_binary_metrics(point["tp"], fp, point["tn"], point["fn"]))
        curve.append(point)
    return sorted(curve, key=lambda item: item["threshold"])


def point_at_threshold(curve: list[dict], threshold: float) -> dict:
    """The curve point whose threshold is closest to the requested one."""
    return min(curve, key=lambda point: abs(point["threshold"] - threshold))


def best_f1_threshold(curve: list[dict]) -> float:
    """Threshold maximising F1; falls back to the default when F1 is undefined."""
    scored = [point for point in curve if point["f1"] is not None]
    if not scored:
        return DEFAULT_THRESHOLD
    return max(scored, key=lambda point: point["f1"])["threshold"]
