"""End-to-end smoke runs of the Phase 5 jobs on synthetic tables in local Spark."""

import csv
import importlib.util
from pathlib import Path

import pytest

pytest.importorskip("pyspark")


JOBS_DIR = Path(__file__).resolve().parents[1] / "jobs"
MODELS_Q7 = {"linear_regression", "gbt_regressor", "persistence"}
MODELS_Q8 = {"logistic_regression", "random_forest", "persistence"}


def _run_job(name, results_dir, extra=()):
    spec = importlib.util.spec_from_file_location(name, JOBS_DIR / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.main(
        [
            "--synthetic",
            "--master",
            "local[2]",
            "--results-dir",
            str(results_dir),
            *extra,
        ]
    )


def _read(results_dir, name):
    with open(results_dir / f"{name}.csv", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


@pytest.fixture(scope="module")
def regression_results(spark, tmp_path_factory):
    results_dir = tmp_path_factory.mktemp("q7")
    _run_job("phase5_regression", results_dir, ["--grid", "quick"])
    return results_dir


@pytest.fixture(scope="module")
def classification_results(spark, tmp_path_factory):
    results_dir = tmp_path_factory.mktemp("q8")
    _run_job("phase5_classification", results_dir, ["--grid", "quick"])
    return results_dir


@pytest.fixture(scope="module")
def kmeans_results(spark, tmp_path_factory):
    results_dir = tmp_path_factory.mktemp("kmeans")
    _run_job("phase5_kmeans", results_dir, ["--k-values", "2", "3", "4"])
    return results_dir


def test_regression_reports_every_model_on_validation_and_test(regression_results):
    metrics = _read(regression_results, "q7_metrics")

    assert {(row["model"], row["split"]) for row in metrics} == {
        (model, split) for model in MODELS_Q7 for split in ("validation", "test")
    }
    for row in metrics:
        assert float(row["rmse"]) > 0
        assert float(row["mae"]) <= float(row["rmse"])
        assert float(row["r2"]) <= 1.0


def test_regression_models_learn_the_synthetic_signal(regression_results):
    test = {
        row["model"]: row
        for row in _read(regression_results, "q7_metrics")
        if row["split"] == "test"
    }

    assert float(test["linear_regression"]["r2"]) > 0.5
    assert float(test["linear_regression"]["rmse"]) < float(test["persistence"]["rmse"])


def test_regression_predictions_cover_only_the_test_years(regression_results):
    predictions = _read(regression_results, "q7_predictions")

    assert predictions
    assert {row["target_date"][:4] for row in predictions} == {"2024", "2025"}
    assert all(row["pred_gbt_regressor"] and row["pred_linear_regression"] for row in predictions)


def test_regression_side_tables(regression_results):
    by_city = _read(regression_results, "q7_metrics_by_city")
    importance = _read(regression_results, "q7_feature_importance")
    tuning = _read(regression_results, "q7_tuning")

    assert {row["city_code"] for row in by_city} == {"KSEA", "KPHX", "KMDW"}
    assert {row["model"] for row in by_city} == MODELS_Q7
    gbt = [row for row in importance if row["model"] == "gbt_regressor"]
    assert sum(float(row["importance"]) for row in gbt) == pytest.approx(1.0)
    features = {row["feature"] for row in gbt}
    assert {
        "tmax_f",
        "doy_sin",
        "h24_temp_mean",
        "tavg_f_lag3",
        "city_code=KSEA",
    } <= features
    assert all(row["selected"] == "True" for row in tuning)
    assert {row["metric"] for row in tuning} == {"rmse"}


def test_classification_metrics_are_consistent(classification_results):
    metrics = _read(classification_results, "q8_metrics")

    assert {row["model"] for row in metrics} == MODELS_Q8
    assert {row["threshold"] for row in metrics} == {"0.5"}
    assert {row["split"] for row in metrics} == {"validation", "test"}
    for row in metrics:
        counts = [int(row[key]) for key in ("tp", "fp", "tn", "fn")]
        assert sum(counts) == int(row["n"])
        assert 0.0 <= float(row["auc_roc"]) <= 1.0
        assert 0.0 <= float(row["auc_pr"]) <= 1.0


def test_classifiers_beat_persistence_on_the_synthetic_signal(classification_results):
    test = {
        row["model"]: row
        for row in _read(classification_results, "q8_metrics")
        if row["split"] == "test"
    }

    assert float(test["logistic_regression"]["auc_roc"]) > 0.8
    assert float(test["logistic_regression"]["auc_roc"]) > float(test["persistence"]["auc_roc"])
    assert float(test["random_forest"]["recall"]) > 0.5


def test_classification_side_tables(classification_results):
    confusion = _read(classification_results, "q8_confusion_matrix")
    curve = _read(classification_results, "q8_roc_curve")
    balance = _read(classification_results, "q8_class_balance")
    by_city = _read(classification_results, "q8_metrics_by_city")
    importance = _read(classification_results, "q8_feature_importance")

    assert len(confusion) == len(MODELS_Q8) * 4
    logistic = [row for row in curve if row["model"] == "logistic_regression"]
    assert len(logistic) == 101
    assert (float(logistic[0]["recall"]), float(logistic[0]["fpr"])) == (1.0, 1.0)
    assert (float(logistic[-1]["recall"]), float(logistic[-1]["fpr"])) == (0.0, 0.0)
    assert {row["split"] for row in balance} == {"train", "validation", "test"}
    assert all(0.0 < float(row["wet_fraction"]) < 1.0 for row in balance)
    assert {row["city_code"] for row in by_city} == {"KSEA", "KPHX", "KMDW"}
    assert {row["model"] for row in importance} == {
        "logistic_regression",
        "random_forest",
    }


def test_kmeans_selects_the_best_silhouette(kmeans_results):
    silhouettes = _read(kmeans_results, "kmeans_silhouette")
    assignments = _read(kmeans_results, "kmeans_assignments")
    features = _read(kmeans_results, "kmeans_city_features")

    assert [row["k"] for row in silhouettes] == ["2", "3", "4"]
    selected = [row for row in silhouettes if row["selected"] == "True"]
    assert len(selected) == 1
    assert float(selected[0]["silhouette"]) == max(float(row["silhouette"]) for row in silhouettes)
    chosen = [row for row in assignments if row["selected"] == "True"]
    assert len(chosen) == 5
    assert len({row["cluster"] for row in chosen}) == int(selected[0]["k"])
    assert len(features) == 5
    assert all(
        row["temp_m07"] and row["prcp_m01"] and row["hourly_amplitude_f"] for row in features
    )
    by_city = {row["city_code"]: row for row in features}
    assert float(by_city["KPHX"]["temp_m07"]) > float(by_city["KSEA"]["temp_m07"])
