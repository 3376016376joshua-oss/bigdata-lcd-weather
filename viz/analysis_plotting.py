"""Shared loading, styling and saving for the question 1-6 figure scripts.

Every script reads result CSVs from the results directory and writes a static PNG
(matplotlib/seaborn) and an interactive HTML page (Plotly) per figure.
"""

from __future__ import annotations

import argparse
import os
from collections.abc import Sequence
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

ENV_RESULTS_DIR = "LCD_RESULTS_DIR"
ENV_FIGURES_DIR = "LCD_FIGURES_DIR"
DEFAULT_RESULTS_DIR = "results"
DEFAULT_FIGURES_DIR = "figures"

PNG_DPI = 150
PLOTLY_TEMPLATE = "plotly_white"
PANEL_COLUMNS = 5
SEASONS = ["DJF", "MAM", "JJA", "SON"]
SEASON_COLORS = {"DJF": "#2166ac", "MAM": "#4dac26", "JJA": "#d6604d", "SON": "#b8860b"}
WARM_COLOR = "#d6604d"
COLD_COLOR = "#4393c3"
NEUTRAL_COLOR = "#7f7f7f"
HIGHLIGHT_COLOR = "#f1c40f"
ALL_CITIES_CODE = "ALL"


def parse_args(description: str, argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument(
        "--results-dir",
        default=os.environ.get(ENV_RESULTS_DIR) or DEFAULT_RESULTS_DIR,
        help="directory holding the q<N>_*.csv result files",
    )
    parser.add_argument(
        "--figures-dir",
        default=os.environ.get(ENV_FIGURES_DIR) or DEFAULT_FIGURES_DIR,
        help="directory the PNG and HTML figures are written to",
    )
    return parser.parse_args(argv)


def apply_style() -> None:
    """Use a file-only backend (no display on the cluster) and one seaborn theme."""
    plt.switch_backend("Agg")
    sns.set_theme(style="whitegrid", context="notebook")


def load_result(results_dir: str, name: str) -> pd.DataFrame:
    path = Path(results_dir) / f"{name}.csv"
    if not path.is_file():
        raise FileNotFoundError(
            f"{path} not found; run scripts/run_phase4.sh to produce the Phase 4 results"
        )
    return pd.read_csv(path)


def save_png(figure, figures_dir: str, name: str) -> Path:
    """Save and close a matplotlib figure as ``<name>.png``."""
    directory = Path(figures_dir)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{name}.png"
    figure.savefig(path, dpi=PNG_DPI, bbox_inches="tight")
    plt.close(figure)
    print(f"wrote {path}")
    return path


def save_html(figure, figures_dir: str, name: str) -> Path:
    """Save a Plotly figure as ``<name>.html`` (plotly.js is loaded from the CDN)."""
    directory = Path(figures_dir)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{name}.html"
    figure.update_layout(template=PLOTLY_TEMPLATE)
    # Plotly Express titles facets "city=Seattle"; keep only the value.
    figure.for_each_annotation(lambda note: note.update(text=note.text.split("=")[-1]))
    figure.write_html(path, include_plotlyjs="cdn")
    print(f"wrote {path}")
    return path


def panel_grid(n_panels: int, panel_width: float = 3.4, panel_height: float = 3.0):
    """Small multiples: a figure and a flat list of ``n_panels`` axes sharing both axes."""
    n_columns = min(PANEL_COLUMNS, n_panels)
    n_rows = -(-n_panels // n_columns)
    figure, axes = plt.subplots(
        n_rows,
        n_columns,
        figsize=(panel_width * n_columns, panel_height * n_rows),
        sharex=True,
        sharey=True,
        squeeze=False,
    )
    flat_axes = list(axes.flat)
    for unused in flat_axes[n_panels:]:
        unused.set_visible(False)
    return figure, flat_axes[:n_panels]


def finish_panels(figure, axes, title: str, x_label: str, y_label: str) -> None:
    """Title, shared axis labels and one legend below the panels of a small-multiples figure."""
    figure.suptitle(title)
    figure.supxlabel(x_label, fontsize="medium")
    figure.supylabel(y_label, fontsize="medium")
    figure.tight_layout()
    handles, labels = axes[0].get_legend_handles_labels()
    figure.legend(
        handles,
        labels,
        loc="upper center",
        bbox_to_anchor=(0.5, 0),
        ncol=len(labels),
        frameon=False,
    )
