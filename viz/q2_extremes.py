"""Question 2 figures: warm and cold extreme days by year and by season.

Reads q2_extreme_days_by_year.csv and q2_extreme_days_by_season.csv. Writes
q2_extreme_days_by_year and q2_extreme_days_by_season as PNG and HTML.
"""

from __future__ import annotations

from collections.abc import Sequence

import pandas as pd
import plotly.express as px
import seaborn as sns
from analysis_plotting import (
    COLD_COLOR,
    PANEL_COLUMNS,
    SEASON_COLORS,
    SEASONS,
    WARM_COLOR,
    apply_style,
    finish_panels,
    load_result,
    panel_grid,
    parse_args,
    save_html,
    save_png,
)

KIND_COLORS = {"Warm extreme": WARM_COLOR, "Cold extreme": COLD_COLOR}
KIND_COLUMNS = {"warm_extreme_days": "Warm extreme", "cold_extreme_days": "Cold extreme"}


def long_format(counts: pd.DataFrame, keys: list[str]) -> pd.DataFrame:
    """One row per city, key and kind of extreme, with the day count in ``days``."""
    melted = counts.melt(
        id_vars=["city", *keys], value_vars=list(KIND_COLUMNS), var_name="kind", value_name="days"
    )
    return melted.assign(kind=melted["kind"].map(KIND_COLUMNS))


def by_year_png(by_year: pd.DataFrame):
    cities = sorted(by_year["city"].unique())
    figure, axes = panel_grid(len(cities))
    for axis, city in zip(axes, cities):
        rows = by_year[by_year["city"] == city].sort_values("yr")
        axis.bar(rows["yr"], rows["warm_extreme_days"], color=WARM_COLOR, label="Warm extreme")
        axis.bar(rows["yr"], -rows["cold_extreme_days"], color=COLD_COLOR, label="Cold extreme")
        axis.axhline(0, color="black", linewidth=0.6)
        axis.set_title(city)
    title = "Days 10 °F or more above or below normal, per city and year (cold below zero)"
    finish_panels(figure, axes, title, "Year", "Extreme days")
    return figure


def by_year_html(by_year: pd.DataFrame):
    return px.bar(
        long_format(by_year, ["yr"]),
        x="yr",
        y="days",
        color="kind",
        facet_col="city",
        facet_col_wrap=PANEL_COLUMNS,
        barmode="group",
        color_discrete_map=KIND_COLORS,
        category_orders={"city": sorted(by_year["city"].unique())},
        labels={"yr": "Year", "days": "Days", "kind": ""},
        title="Days 10 °F or more above or below normal, per city and year",
    )


def by_season_png(by_season: pd.DataFrame):
    grid = sns.catplot(
        data=long_format(by_season, ["season"]),
        kind="bar",
        x="city",
        y="days",
        hue="season",
        hue_order=SEASONS,
        palette=SEASON_COLORS,
        col="kind",
        height=4.2,
        aspect=1.5,
    )
    grid.set_axis_labels("", "Extreme days, 2010-2025")
    grid.set_titles("{col_name} days by season")
    grid.legend.set_title("Season")
    for axis in grid.axes.flat:
        axis.tick_params(axis="x", rotation=45)
    return grid.figure


def by_season_html(by_season: pd.DataFrame):
    return px.bar(
        long_format(by_season, ["season"]),
        x="city",
        y="days",
        color="season",
        facet_col="kind",
        barmode="group",
        color_discrete_map=SEASON_COLORS,
        category_orders={"season": SEASONS},
        labels={"city": "", "days": "Extreme days, 2010-2025", "season": "Season"},
        title="Seasons of the warm and cold extreme days",
    )


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(__doc__.splitlines()[0], argv)
    apply_style()
    by_year = load_result(args.results_dir, "q2_extreme_days_by_year")
    by_season = load_result(args.results_dir, "q2_extreme_days_by_season")
    save_png(by_year_png(by_year), args.figures_dir, "q2_extreme_days_by_year")
    save_html(by_year_html(by_year), args.figures_dir, "q2_extreme_days_by_year")
    save_png(by_season_png(by_season), args.figures_dir, "q2_extreme_days_by_season")
    save_html(by_season_html(by_season), args.figures_dir, "q2_extreme_days_by_season")


if __name__ == "__main__":
    main()
