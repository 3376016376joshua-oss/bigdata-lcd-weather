"""Smoke tests: every Phase 5-6 figure script renders from small result CSVs."""

import csv
import importlib
from pathlib import Path

import pytest

pytest.importorskip("matplotlib")
pytest.importorskip("pandas")

VIZ_DIR = Path(__file__).resolve().parents[1] / "viz"
CITIES = ("KSEA", "KPHX")
Q7_MODELS = ("linear_regression", "gbt_regressor", "persistence")
Q8_MODELS = ("logistic_regression", "random_forest", "persistence")


def _write(folder, name, rows):
    with open(folder / f"{name}.csv", "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _run(monkeypatch, script, results, figures, extra=()):
    monkeypatch.syspath_prepend(str(VIZ_DIR))
    module = importlib.import_module(script)
    module.main(["--results-dir", str(results), "--figures-dir", str(figures), *extra])
    return sorted(path.name for path in figures.glob("*.png"))


def _importance(models):
    return [
        {
            "model": model,
            "feature": f"feature_{i}",
            "importance": 1 / (i + 1),
            "signed_value": 0.1,
        }
        for model in models
        for i in range(4)
    ]


def test_regression_figures(tmp_path, monkeypatch):
    _write(
        tmp_path,
        "q7_metrics",
        [
            {
                "model": model,
                "split": split,
                "n": 10,
                "rmse": 4.0 + i,
                "mae": 3.0 + i,
                "r2": 0.9 - i / 10,
            }
            for split in ("validation", "test")
            for i, model in enumerate(Q7_MODELS)
        ],
    )
    _write(
        tmp_path,
        "q7_metrics_by_city",
        [
            {
                "model": model,
                "split": "test",
                "city_code": city,
                "n": 5,
                "rmse": 4.0,
                "mae": 3.0,
                "r2": 0.9,
            }
            for model in Q7_MODELS
            for city in CITIES
        ],
    )
    _write(
        tmp_path,
        "q7_predictions",
        [
            {
                "city_code": "KSEA",
                "label": 50.0 + i,
                "pred_linear_regression": 51.0 + i,
                "pred_gbt_regressor": 49.0 + i,
                "pred_persistence": 50.5 + i,
            }
            for i in range(6)
        ],
    )
    _write(tmp_path, "q7_feature_importance", _importance(Q7_MODELS[:2]))

    figures = _run(monkeypatch, "ml_regression", tmp_path, tmp_path / "figures")

    assert figures == [
        "ml_q7_feature_importance.png",
        "ml_q7_metrics.png",
        "ml_q7_predicted_vs_actual.png",
        "ml_q7_rmse_by_city.png",
    ]


def test_classification_figures(tmp_path, monkeypatch):
    _write(
        tmp_path,
        "q8_metrics",
        [
            {
                "model": model,
                "split": "test",
                "threshold_rule": rule,
                "threshold": 0.5,
                "auc_roc": 0.8,
                "auc_pr": 0.6,
                "precision": "" if model == "persistence" else 0.7,
                "recall": 0.6,
                "f1": 0.65,
            }
            for model in Q8_MODELS
            for rule in ("default_0.5", "validation_f1")
        ],
    )
    _write(
        tmp_path,
        "q8_roc_curve",
        [
            {
                "model": model,
                "threshold": i / 4,
                "fpr": 1 - i / 4,
                "recall": 1 - (i / 4) ** 2,
                "precision": "" if i == 4 else 0.3 + i / 8,
                "f1": 0.5,
            }
            for model in Q8_MODELS
            for i in range(5)
        ],
    )
    _write(
        tmp_path,
        "q8_confusion_matrix",
        [
            {
                "model": model,
                "threshold_rule": "validation_f1",
                "threshold": 0.4,
                "actual": actual,
                "predicted": predicted,
                "count": count,
            }
            for model in Q8_MODELS
            for actual, predicted, count in (
                ("wet", "wet", 30),
                ("dry", "wet", 5),
                ("dry", "dry", 60),
                ("wet", "dry", 9),
            )
        ],
    )
    _write(tmp_path, "q8_feature_importance", _importance(Q8_MODELS[:2]))
    _write(
        tmp_path,
        "q8_class_balance",
        [
            {"split": "test", "city_code": city, "n_days": 100, "n_wet": 30, "wet_fraction": 0.3}
            for city in CITIES
        ],
    )

    figures = _run(monkeypatch, "ml_classification", tmp_path, tmp_path / "figures")

    assert figures == [
        "ml_q8_class_balance.png",
        "ml_q8_confusion.png",
        "ml_q8_feature_importance.png",
        "ml_q8_metrics.png",
        "ml_q8_roc_pr.png",
    ]


def _kmeans_results(folder):
    _write(
        folder,
        "kmeans_silhouette",
        [
            {"k": 2, "silhouette": 0.5, "within_cluster_sse": 40.0, "selected": True},
            {"k": 3, "silhouette": 0.3, "within_cluster_sse": 20.0, "selected": False},
        ],
    )
    rows = []
    for cluster, city in enumerate(CITIES):
        row = {"city_code": city, "city": city, "cluster": cluster}
        for month in range(1, 13):
            row[f"temp_m{month:02d}"] = 50.0 + month + 10 * cluster
            row[f"prcp_m{month:02d}"] = 1.0 + cluster
        rows.append(row)
    _write(folder, "kmeans_city_features", rows)


def test_kmeans_figures_with_and_without_station_coordinates(tmp_path, monkeypatch):
    _kmeans_results(tmp_path)
    stations = tmp_path / "stations.csv"
    stations.write_text(
        "station_id,city,city_code,state,lat,lon,start_year,end_year\n"
        "A,Seattle,KSEA,WA,47.4,-122.3,2010,2025\n"
        "B,Phoenix,KPHX,AZ,33.4,-112.0,2010,2025\n",
        encoding="utf-8",
    )

    without_map = _run(
        monkeypatch,
        "ml_kmeans",
        tmp_path,
        tmp_path / "plain",
        ["--stations", str(tmp_path / "missing.csv")],
    )
    with_map = _run(
        monkeypatch, "ml_kmeans", tmp_path, tmp_path / "mapped", ["--stations", str(stations)]
    )

    assert without_map == ["ml_kmeans_profiles.png", "ml_kmeans_silhouette.png"]
    assert with_map == [
        "ml_kmeans_map.png",
        "ml_kmeans_profiles.png",
        "ml_kmeans_silhouette.png",
    ]


def test_line_end_labels_are_spread_apart(monkeypatch):
    monkeypatch.syspath_prepend(str(VIZ_DIR))
    spread_labels = importlib.import_module("ml_kmeans").spread_labels

    placed = spread_labels({"A": 10.0, "B": 10.2, "C": 30.0, "D": 10.1}, min_gap=1.0)

    assert placed == {"A": 10.0, "D": 11.0, "B": 12.0, "C": 30.0}


def test_timing_figure(tmp_path, monkeypatch):
    _write(
        tmp_path,
        "runtime_scaling_summary",
        [
            {
                "job": job,
                "n_years": years,
                "runs": 1,
                "input_gb": years * 0.09,
                "median_wall_seconds": base * years**0.8,
                "loglog_slope": 0.8,
            }
            for job, base in (("ingest", 60.0), ("analysis", 40.0))
            for years in (1, 4, 8, 16)
        ],
    )

    figures = _run(monkeypatch, "timing_scaling", tmp_path, tmp_path / "figures")

    assert figures == ["timing_runtime_scaling.png"]


def test_missing_result_file_names_the_job_output(tmp_path, monkeypatch):
    monkeypatch.syspath_prepend(str(VIZ_DIR))
    read_result = importlib.import_module("ml_plotting").read_result

    with pytest.raises(FileNotFoundError, match="q7_metrics"):
        read_result(str(tmp_path), "q7_metrics")
