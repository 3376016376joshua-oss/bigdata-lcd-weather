import pytest

from lcdweather.ml.binary_metrics import (
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


def test_derive_binary_metrics_without_positive_predictions():
    metrics = derive_binary_metrics(tp=0, fp=0, tn=5, fn=3)

    assert metrics["precision"] is None
    assert metrics["f1"] == 0.0
    assert metrics["recall"] == 0.0


def test_f1_is_zero_without_true_positives():
    assert derive_binary_metrics(tp=0, fp=4, tn=5, fn=3)["f1"] == 0.0
    assert derive_binary_metrics(tp=0, fp=4, tn=5, fn=0)["f1"] == 0.0


def test_f1_is_undefined_only_without_positives_of_either_kind():
    assert derive_binary_metrics(tp=0, fp=0, tn=5, fn=0)["f1"] is None


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
