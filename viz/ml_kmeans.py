"""Climate clustering figures: silhouette by k, monthly profiles, city map.

python viz/ml_kmeans.py --results-dir results --figures-dir figures
"""

from __future__ import annotations

import os
from collections.abc import Sequence

import matplotlib.pyplot as plt
import pandas as pd
from ml_plotting import (
    INK,
    SERIES_COLORS,
    parse_args,
    read_result,
    save_figure,
)

MONTH_LABELS = ("J", "F", "M", "A", "M", "J", "J", "A", "S", "O", "N", "D")
MONTHS = range(1, 13)
LABEL_GAP_SHARE = 0.035
PROFILE_PANELS = (
    ("temp", "Mean temperature (°F)"),
    ("prcp", "Mean monthly precipitation (in)"),
)


def _cluster_color(cluster) -> str:
    return SERIES_COLORS[int(cluster) % len(SERIES_COLORS)]


def spread_labels(positions: dict, min_gap: float) -> dict:
    """Nudge line-end labels apart so that none overlap, keeping their order."""
    placed = {}
    previous = None
    for name, value in sorted(positions.items(), key=lambda item: item[1]):
        height = value if previous is None else max(value, previous + min_gap)
        placed[name] = height
        previous = height
    return placed


def plot_silhouette(silhouette):
    figure, ax = plt.subplots(figsize=(4.8, 3.2))
    ax.plot(
        silhouette["k"],
        silhouette["silhouette"],
        marker="o",
        markersize=7,
        color=SERIES_COLORS[0],
    )
    chosen = silhouette[silhouette["selected"].astype(str) == "True"]
    for _, row in chosen.iterrows():
        ax.annotate(
            f"selected k = {int(row['k'])}",
            (row["k"], row["silhouette"]),
            textcoords="offset points",
            xytext=(10, 6),
            color=INK,
        )
    ax.margins(y=0.2)
    ax.set_xticks(silhouette["k"].tolist())
    ax.set(
        xlabel="Number of clusters k",
        ylabel="Silhouette score",
        title="K-means silhouette by k",
    )
    figure.tight_layout()
    return figure


def plot_profiles(features):
    figure, axes = plt.subplots(1, len(PROFILE_PANELS), figsize=(10.5, 4.2))
    for ax, (prefix, label) in zip(axes, PROFILE_PANELS):
        columns = [f"{prefix}_m{month:02d}" for month in MONTHS]
        ends = {}
        for _, city in features.iterrows():
            values = city[columns].astype(float).tolist()
            ax.plot(
                list(MONTHS),
                values,
                color=_cluster_color(city["cluster"]),
                linewidth=1.6,
            )
            ends[city["city_code"]] = values[-1]
        low, high = ax.get_ylim()
        label_heights = spread_labels(ends, (high - low) * LABEL_GAP_SHARE)
        for city_code, height in label_heights.items():
            ax.annotate(
                city_code,
                (12, height),
                textcoords="offset points",
                xytext=(4, 0),
                va="center",
                fontsize=7,
            )
        ax.set_xticks(list(MONTHS), MONTH_LABELS)
        ax.set_title(label)
        ax.margins(x=0.08)
    clusters = sorted(features["cluster"].unique())
    handles = [
        plt.Line2D([], [], color=_cluster_color(c), label=f"Cluster {int(c)}") for c in clusters
    ]
    figure.legend(
        handles=handles,
        ncols=len(handles),
        loc="lower left",
        bbox_to_anchor=(0.01, 0.97),
    )
    figure.tight_layout()
    return figure


def plot_map(features, stations):
    located = stations.drop_duplicates("city_code").merge(features, on="city_code")
    figure, ax = plt.subplots(figsize=(8, 4.6))
    colors = [_cluster_color(cluster) for cluster in located["cluster"]]
    ax.scatter(
        located["lon"],
        located["lat"],
        s=90,
        c=colors,
        edgecolors="#fcfcfb",
        linewidths=2,
    )
    for _, row in located.iterrows():
        ax.annotate(
            row["city_code"],
            (row["lon"], row["lat"]),
            textcoords="offset points",
            xytext=(7, 5),
        )
    clusters = sorted(located["cluster"].unique())
    handles = [
        plt.Line2D(
            [],
            [],
            marker="o",
            linestyle="",
            color=_cluster_color(c),
            label=f"Cluster {int(c)}",
        )
        for c in clusters
    ]
    ax.legend(handles=handles, loc="upper left", bbox_to_anchor=(1.01, 1))
    ax.set(
        xlabel="Longitude",
        ylabel="Latitude",
        title="Climate clusters of the ten cities",
    )
    ax.margins(0.12)
    figure.tight_layout()
    return figure


def _add_stations_argument(parser) -> None:
    parser.add_argument(
        "--stations", default="config/stations.csv", help="station list with lat / lon"
    )


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(__doc__, argv, extra=_add_stations_argument)
    features = read_result(args.results_dir, "kmeans_city_features")
    silhouette = read_result(args.results_dir, "kmeans_silhouette")
    save_figure(plot_silhouette(silhouette), args.figures_dir, "ml_kmeans_silhouette")
    save_figure(plot_profiles(features), args.figures_dir, "ml_kmeans_profiles")
    if os.path.exists(args.stations):
        stations = pd.read_csv(args.stations)
        save_figure(plot_map(features, stations), args.figures_dir, "ml_kmeans_map")
    else:
        print(f"{args.stations} not found; skipping the cluster map")


if __name__ == "__main__":
    main()
