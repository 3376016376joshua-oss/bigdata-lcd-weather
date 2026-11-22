"""Question 8 figures: metrics, ROC / PR curves, confusion matrices, importance.

python viz/ml_classification.py --results-dir results --figures-dir figures
"""

from __future__ import annotations

from collections.abc import Sequence

import matplotlib.pyplot as plt
import numpy as np
from ml_plotting import (
    AXIS_COLOR,
    INK,
    SEQUENTIAL_CMAP,
    SERIES_COLORS,
    horizontal_bars,
    model_color,
    model_label,
    model_metric_panels,
    parse_args,
    read_result,
    save_figure,
    top_features,
)

TREE_MODEL = "random_forest"
TOP_FEATURES = 15
TUNED_RULE = "validation_f1"
CLASSES = ("dry", "wet")
METRIC_LABELS = {
    "auc_roc": "ROC AUC",
    "auc_pr": "PR AUC",
    "precision": "Precision",
    "recall": "Recall",
    "f1": "F1",
}
LIGHT_TEXT_ABOVE_SHARE = 0.55


def _tuned_test(metrics):
    return metrics[(metrics["split"] == "test") & (metrics["threshold_rule"] == TUNED_RULE)]


def plot_metrics(metrics):
    title = "Next-day measurable precipitation: test 2024-2025"
    return model_metric_panels(_tuned_test(metrics).fillna(0.0), METRIC_LABELS, title)


def plot_curves(curve):
    figure, (roc, pr) = plt.subplots(1, 2, figsize=(8.4, 4))
    for model, points in curve.groupby("model", sort=False):
        if points["threshold"].nunique() < 3 or model == "persistence":
            continue
        style = {"color": model_color(model), "label": model_label(model)}
        roc.plot(points["fpr"], points["recall"], **style)
        defined = points.dropna(subset=["precision"])
        pr.plot(defined["recall"], defined["precision"], **style)
    roc.plot([0, 1], [0, 1], color=AXIS_COLOR, linewidth=1, linestyle="--", label="Chance")
    roc.set(
        xlabel="False positive rate",
        ylabel="True positive rate (recall)",
        title="ROC curve",
    )
    pr.set(xlabel="Recall", ylabel="Precision", title="Precision-recall curve")
    roc.legend(loc="lower right")
    figure.tight_layout()
    return figure


def plot_confusion(confusion):
    tuned = confusion[confusion["threshold_rule"] == TUNED_RULE]
    models = list(dict.fromkeys(tuned["model"]))
    figure, axes = plt.subplots(1, len(models), figsize=(3.2 * len(models), 3.3))
    for ax, model in zip(np.atleast_1d(axes), models):
        rows = tuned[tuned["model"] == model]
        matrix = rows.pivot(index="actual", columns="predicted", values="count")
        matrix = matrix.reindex(index=CLASSES, columns=CLASSES).fillna(0)
        ax.imshow(matrix.to_numpy(), cmap=SEQUENTIAL_CMAP, vmin=0)
        peak = max(float(matrix.to_numpy().max()), 1.0)
        for (row, column), count in np.ndenumerate(matrix.to_numpy()):
            light = count / peak > LIGHT_TEXT_ABOVE_SHARE
            ax.text(
                column,
                row,
                f"{int(count):,}",
                ha="center",
                va="center",
                color="#ffffff" if light else INK,
            )
        ax.set_xticks(range(len(CLASSES)), CLASSES)
        ax.set_yticks(range(len(CLASSES)), CLASSES)
        ax.set(xlabel="Predicted", ylabel="Actual", title=model_label(model))
        ax.grid(visible=False)
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


def plot_class_balance(balance):
    test = balance[balance["split"] == "test"].sort_values("wet_fraction", ascending=False)
    figure, ax = plt.subplots(figsize=(6, 0.3 * len(test) + 1.2))
    colors = [SERIES_COLORS[0]] * len(test)
    horizontal_bars(ax, test["city_code"].tolist(), test["wet_fraction"].tolist(), colors)
    ax.set_title("Share of days with measurable precipitation (test 2024-2025)")
    figure.tight_layout()
    return figure


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(__doc__, argv)
    figures = {
        "ml_q8_metrics": plot_metrics(read_result(args.results_dir, "q8_metrics")),
        "ml_q8_roc_pr": plot_curves(read_result(args.results_dir, "q8_roc_curve")),
        "ml_q8_confusion": plot_confusion(read_result(args.results_dir, "q8_confusion_matrix")),
        "ml_q8_feature_importance": plot_feature_importance(
            read_result(args.results_dir, "q8_feature_importance")
        ),
        "ml_q8_class_balance": plot_class_balance(
            read_result(args.results_dir, "q8_class_balance")
        ),
    }
    for name, figure in figures.items():
        save_figure(figure, args.figures_dir, name)


if __name__ == "__main__":
    main()
