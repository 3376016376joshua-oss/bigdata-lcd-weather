"""Shared loading, styling and saving for the Phase 5-6 figures."""

from __future__ import annotations

import argparse
import os
from collections.abc import Sequence

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

SERIES_COLORS = (
    "#2a78d6",
    "#eb6834",
    "#1baf7a",
    "#eda100",
    "#e87ba4",
    "#008300",
    "#6250d6",
    "#e34948",
)
BASELINE_COLOR = "#898781"
SEQUENTIAL_CMAP = "Blues"
INK = "#0b0b0b"
SECONDARY_INK = "#52514e"
GRID_COLOR = "#e1e0d9"
AXIS_COLOR = "#c3c2b7"
SURFACE = "#fcfcfb"
FIGURE_DPI = 150
# Colour follows the model, not its position in a table.
MODEL_COLORS = {
    "linear_regression": SERIES_COLORS[0],
    "logistic_regression": SERIES_COLORS[0],
    "gbt_regressor": SERIES_COLORS[1],
    "random_forest": SERIES_COLORS[1],
    "persistence": BASELINE_COLOR,
}
MODEL_LABELS = {
    "linear_regression": "Linear regression",
    "logistic_regression": "Logistic regression",
    "gbt_regressor": "Gradient-boosted trees",
    "random_forest": "Random forest",
    "persistence": "Persistence baseline",
}

plt.rcParams.update(
    {
        "figure.facecolor": SURFACE,
        "axes.facecolor": SURFACE,
        "savefig.facecolor": SURFACE,
        "axes.edgecolor": AXIS_COLOR,
        "axes.labelcolor": SECONDARY_INK,
        "axes.titlecolor": INK,
        "axes.titleweight": "bold",
        "axes.titlesize": 11,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "axes.axisbelow": True,
        "grid.color": GRID_COLOR,
        "grid.linewidth": 0.6,
        "xtick.color": SECONDARY_INK,
        "ytick.color": SECONDARY_INK,
        "text.color": INK,
        "font.size": 9,
        "lines.linewidth": 2.0,
        "legend.frameon": False,
    }
)


def parse_args(description: str, argv: Sequence[str] | None = None, extra=None):
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--results-dir", default="results")
    parser.add_argument("--figures-dir", default="figures")
    if extra is not None:
        extra(parser)
    return parser.parse_args(argv)


def read_result(results_dir: str, name: str) -> pd.DataFrame:
    path = os.path.join(results_dir, f"{name}.csv")
    if not os.path.exists(path):
        raise FileNotFoundError(f"{path} not found; run the job that exports {name} first")
    return pd.read_csv(path)


def save_figure(figure, figures_dir: str, name: str) -> str:
    os.makedirs(figures_dir, exist_ok=True)
    path = os.path.join(figures_dir, f"{name}.png")
    figure.savefig(path, dpi=FIGURE_DPI, bbox_inches="tight")
    plt.close(figure)
    print(f"wrote {path}")
    return path


def model_label(model: str) -> str:
    return MODEL_LABELS.get(model, model)


def model_color(model: str) -> str:
    return MODEL_COLORS.get(model, SERIES_COLORS[2])


def horizontal_bars(ax, labels, values, colors, value_format: str = "{:.2f}") -> None:
    """Thin horizontal bars with the value written at each bar end."""
    positions = range(len(labels))
    bars = ax.barh(positions, values, color=colors, height=0.55)
    ax.set_yticks(list(positions), labels)
    ax.invert_yaxis()
    ax.grid(axis="y", visible=False)
    ax.bar_label(bars, labels=[value_format.format(v) for v in values], padding=3, color=INK)
    ax.margins(x=0.15)


def model_metric_panels(table: pd.DataFrame, metrics: dict, title: str):
    """One small bar panel per metric, one bar per model (rows of `table`)."""
    figure, axes = plt.subplots(1, len(metrics), figsize=(3.6 * len(metrics), 2.6), sharey=True)
    labels = [model_label(model) for model in table["model"]]
    colors = [model_color(model) for model in table["model"]]
    for ax, (column, label) in zip(axes, metrics.items()):
        horizontal_bars(ax, labels, table[column].tolist(), colors)
        ax.set_title(label)
    figure.suptitle(title, x=0.01, ha="left", fontsize=12, fontweight="bold")
    figure.tight_layout()
    return figure


def top_features(importance: pd.DataFrame, model: str, limit: int) -> pd.DataFrame:
    rows = importance[importance["model"] == model]
    return rows.sort_values("importance", ascending=False).head(limit)
