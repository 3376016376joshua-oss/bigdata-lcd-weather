"""Question 7 figures: model metrics, predicted vs actual, feature importance.

python viz/ml_regression.py --results-dir results --figures-dir figures
"""

from __future__ import annotations

from collections.abc import Sequence

import matplotlib.pyplot as plt
import numpy as np
from ml_plotting import (
    AXIS_COLOR,
    horizontal_bars,
    model_color,
    model_label,
    model_metric_panels,
    parse_args,
    read_result,
    save_figure,
    top_features,
)

TREE_MODEL = "gbt_regressor"
TOP_FEATURES = 15
METRIC_LABELS = {"rmse": "RMSE (°F)", "mae": "MAE (°F)", "r2": "R²"}
BAR_GROUP_WIDTH = 0.8
MODEL_ORDER = ("linear_regression", "gbt_regressor", "persistence")


def plot_metrics(metrics):
    test = metrics[metrics["split"] == "test"]
    title = "Next-day maximum temperature: test 2024-2025"
    return model_metric_panels(test, METRIC_LABELS, title)


def plot_predicted_vs_actual(predictions):
    columns = [name for name in predictions.columns if name.startswith("pred_")]
    figure, axes = plt.subplots(
        1, len(columns), figsize=(3.6 * len(columns), 3.8), sharex=True, sharey=True
    )
    low = float(predictions["label"].min())
    high = float(predictions["label"].max())
    for ax, column in zip(np.atleast_1d(axes), columns):
        model = column[len("pred_") :]
        ax.scatter(
            predictions["label"],
            predictions[column],
            s=5,
            alpha=0.25,
            color=model_color(model),
            linewidths=0,
        )
        ax.plot([low, high], [low, high], color=AXIS_COLOR, linewidth=1)
        ax.set_title(model_label(model))
        ax.set_xlabel("Actual next-day max (°F)")
    np.atleast_1d(axes)[0].set_ylabel("Predicted (°F)")
    figure.tight_layout()
    return figure


def plot_feature_importance(importance):
    top = top_features(importance, TREE_MODEL, TOP_FEATURES)
    figure, ax = plt.subplots(figsize=(6.5, 0.3 * len(top) + 1.2))
    colors = [model_color(TREE_MODEL)] * len(top)
    horizontal_bars(ax, top["feature"].tolist(), top["importance"].tolist(), colors, "{:.3f}")
    ax.set_title(f"{model_label(TREE_MODEL)}: top {len(top)} feature importances")
    figure.tight_layout()
    return figure


def plot_rmse_by_city(by_city):
    table = by_city.pivot(index="city_code", columns="model", values="rmse")
    table = table[[model for model in MODEL_ORDER if model in table.columns]]
    figure, ax = plt.subplots(figsize=(8, 3.4))
    width = BAR_GROUP_WIDTH / len(table.columns)
    positions = np.arange(len(table.index))
    for offset, model in enumerate(table.columns):
        ax.bar(
            positions + offset * width,
            table[model],
            width=width * 0.9,
            color=model_color(model),
            label=model_label(model),
        )
    ax.set_xticks(positions + BAR_GROUP_WIDTH / 2 - width / 2, table.index)
    ax.grid(axis="x", visible=False)
    ax.set_ylabel("Test RMSE (°F)")
    ax.set_title("Next-day maximum temperature error by city")
    ax.legend(ncols=len(table.columns), loc="upper left", bbox_to_anchor=(0, -0.12))
    figure.tight_layout()
    return figure


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(__doc__, argv)
    figures = {
        "ml_q7_metrics": plot_metrics(read_result(args.results_dir, "q7_metrics")),
        "ml_q7_predicted_vs_actual": plot_predicted_vs_actual(
            read_result(args.results_dir, "q7_predictions")
        ),
        "ml_q7_feature_importance": plot_feature_importance(
            read_result(args.results_dir, "q7_feature_importance")
        ),
        "ml_q7_rmse_by_city": plot_rmse_by_city(
            read_result(args.results_dir, "q7_metrics_by_city")
        ),
    }
    for name, figure in figures.items():
        save_figure(figure, args.figures_dir, name)


if __name__ == "__main__":
    main()
