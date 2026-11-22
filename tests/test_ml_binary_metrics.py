import pytest

from lcdweather.ml.binary_metrics import (
    DEFAULT_THRESHOLD,
    best_f1_threshold,
    curve_from_histogram,
    derive_binary_metrics,
    point_at_threshold,
)


def test_derive_binary_metrics_matches_hand_computation():
    metrics = derive_binary_metrics(tp=6, fp=2, tn=10, fn=2)

    assert metrics["precision"] == pytest.approx(0.75)
    assert metrics["recall"] == pytest.approx(0.75)
    assert metrics["f1"] == pytest.approx(0.75)
    assert metrics["accuracy"] == pytest.approx(0.8)
    assert metrics["fpr"] == pytest.approx(2 / 12)


def test_derive_binary_metrics_is_undefined_without_positive_predictions():
    metrics = derive_binary_metrics(tp=0, fp=0, tn=5, fn=3)

    assert metrics["precision"] is None
    assert metrics["f1"] is None
    assert metrics["recall"] == 0.0


def test_curve_counts_are_cumulative_from_the_highest_score_bin():
    # bin -> (positives, rows) with 10 bins: scores 0.05, 0.55 and 0.95.
    histogram = {0: (1, 4), 5: (1, 2), 9: (3, 3)}

    curve = curve_from_histogram(histogram, n_bins=10)

    assert [point["threshold"] for point in curve] == [i / 10 for i in range(11)]
    everything_positive = curve[0]
    assert (everything_positive["tp"], everything_positive["fp"]) == (5, 4)
    assert (everything_positive["tn"], everything_positive["fn"]) == (0, 0)
    middle = point_at_threshold(curve, 0.5)
    assert (middle["tp"], middle["fp"], middle["tn"], middle["fn"]) == (4, 1, 3, 1)
    nothing_positive = curve[-1]
    assert (nothing_positive["tp"], nothing_positive["fp"]) == (0, 0)
    assert nothing_positive["fn"] == 5


def test_curve_rates_are_monotonic_in_the_threshold():
    histogram = {0: (0, 5), 3: (2, 6), 7: (4, 5), 9: (5, 5)}

    curve = curve_from_histogram(histogram, n_bins=10)

    recalls = [point["recall"] for point in curve]
    false_positive_rates = [point["fpr"] for point in curve]
    assert recalls == sorted(recalls, reverse=True)
    assert false_positive_rates == sorted(false_positive_rates, reverse=True)


def test_best_f1_threshold_picks_the_separating_threshold():
    histogram = {1: (0, 10), 8: (10, 10)}

    curve = curve_from_histogram(histogram, n_bins=10)

    best = point_at_threshold(curve, best_f1_threshold(curve))
    assert best["f1"] == pytest.approx(1.0)
    assert 0.2 <= best["threshold"] <= 0.8


def test_best_f1_threshold_falls_back_when_there_are_no_positives():
    curve = curve_from_histogram({0: (0, 3)}, n_bins=10)

    assert best_f1_threshold(curve) == DEFAULT_THRESHOLD
