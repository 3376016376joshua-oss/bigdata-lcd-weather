"""Question 1 figures: temperature anomaly heatmap and the West/East pattern.

Reads q1_monthly_anomaly.csv and q1_west_east_pattern.csv. Writes
q1_anomaly_heatmap and q1_west_east_pattern as PNG and HTML.
"""

from __future__ import annotations

from collections.abc import Sequence

import matplotlib.pyplot as plt
import pandas as pd
import plotly.graph_objects as go
import seaborn as sns
from analysis_plotting import (
    COLD_COLOR,
    HIGHLIGHT_COLOR,
    WARM_COLOR,
    apply_style,
    load_result,
    parse_args,
    save_html,
    save_png,
)

MONTHS_PER_YEAR = 12
HEATMAP_LIMIT_F = 10


def anomaly_matrix(monthly: pd.DataFrame) -> pd.DataFrame:
    """Cities as rows and YYYY-MM months as columns."""
    labelled = monthly.assign(
        period=monthly["yr"].astype(str) + "-" + monthly["mo"].astype(str).str.zfill(2)
    )
    return labelled.pivot(index="city", columns="period", values="anomaly_f").sort_index()


def heatmap_png(matrix: pd.DataFrame):
    figure, axis = plt.subplots(figsize=(16, 4.8))
    sns.heatmap(
        matrix,
        ax=axis,
        cmap="RdBu_r",
        center=0,
        vmin=-HEATMAP_LIMIT_F,
        vmax=HEATMAP_LIMIT_F,
        cbar_kws={"label": "Departure from normal (°F)"},
    )
    january = [i for i, period in enumerate(matrix.columns) if period.endswith("-01")]
    ticks = january or list(range(0, len(matrix.columns), MONTHS_PER_YEAR))
    axis.set_xticks([tick + 0.5 for tick in ticks])
    axis.set_xticklabels([matrix.columns[tick][:4] for tick in ticks], rotation=0)
    axis.set_xlabel("Month")
    axis.set_ylabel("")
    axis.set_title("Monthly temperature anomaly by city")
    return figure


def heatmap_html(matrix: pd.DataFrame):
    figure = go.Figure(
        go.Heatmap(
            z=matrix.to_numpy(),
            x=list(matrix.columns),
            y=list(matrix.index),
            colorscale="RdBu",
            reversescale=True,
            zmid=0,
            colorbar={"title": "°F"},
            hovertemplate="%{y} %{x}: %{z:.1f} °F<extra></extra>",
        )
    )
    figure.update_layout(title="Monthly temperature anomaly by city", xaxis_title="Month")
    return figure


def pattern_png(pattern: pd.DataFrame):
    figure, axis = plt.subplots(figsize=(11, 4.5))
    positions = range(len(pattern))
    width = 0.4
    axis.bar(
        [p - width / 2 for p in positions],
        pattern["west_anomaly_f"],
        width,
        color=WARM_COLOR,
        label="West (Los Angeles, Phoenix, Seattle)",
    )
    axis.bar(
        [p + width / 2 for p in positions],
        pattern["east_anomaly_f"],
        width,
        color=COLD_COLOR,
        label="East (Chicago, Indianapolis, New York, Philadelphia)",
    )
    for position, flagged in zip(positions, pattern["is_2014_15"]):
        if flagged:
            axis.axvspan(position - 0.5, position + 0.5, color=HIGHLIGHT_COLOR, alpha=0.25)
    axis.axhline(0, color="black", linewidth=0.8)
    axis.set_xticks(list(positions))
    axis.set_xticklabels(pattern["period_label"], rotation=45, ha="right")
    axis.set_ylabel("Mean departure from normal (°F)")
    axis.set_title("West and East temperature anomaly by July-June year (2014-15 highlighted)")
    axis.legend(loc="best")
    return figure


def pattern_html(pattern: pd.DataFrame):
    figure = go.Figure()
    for column, label, color in (
        ("west_anomaly_f", "West", WARM_COLOR),
        ("east_anomaly_f", "East", COLD_COLOR),
    ):
        figure.add_bar(x=pattern["period_label"], y=pattern[column], name=label, marker_color=color)
    figure.add_scatter(
        x=pattern["period_label"],
        y=pattern["west_minus_east_f"],
        name="West minus East",
        mode="lines+markers",
        line={"color": "black"},
        customdata=pattern[["contrast_rank", "n_periods"]].to_numpy(),
        hovertemplate="%{x}: %{y:.1f} °F, rank %{customdata[0]} of %{customdata[1]}",
    )
    figure.update_layout(
        barmode="group",
        title="West and East temperature anomaly by July-June year",
        yaxis_title="Mean departure from normal (°F)",
    )
    return figure


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(__doc__.splitlines()[0], argv)
    apply_style()
    matrix = anomaly_matrix(load_result(args.results_dir, "q1_monthly_anomaly"))
    pattern = load_result(args.results_dir, "q1_west_east_pattern").sort_values("start_yr")
    save_png(heatmap_png(matrix), args.figures_dir, "q1_anomaly_heatmap")
    save_html(heatmap_html(matrix), args.figures_dir, "q1_anomaly_heatmap")
    save_png(pattern_png(pattern), args.figures_dir, "q1_west_east_pattern")
    save_html(pattern_html(pattern), args.figures_dir, "q1_west_east_pattern")


if __name__ == "__main__":
    main()
