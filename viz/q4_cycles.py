"""Question 4 figures: hour-by-hour and seasonal temperature cycles per city.

Reads q4_hourly_profile.csv and q4_monthly_climatology.csv. Writes q4_hourly_cycle
(small multiples) and q4_monthly_climatology as PNG and HTML.
"""

from __future__ import annotations

from collections.abc import Sequence

import matplotlib.pyplot as plt
import pandas as pd
import plotly.express as px
import seaborn as sns
from analysis_plotting import (
    PANEL_COLUMNS,
    SEASON_COLORS,
    SEASONS,
    apply_style,
    finish_panels,
    load_result,
    panel_grid,
    parse_args,
    save_html,
    save_png,
)

HOUR_TICKS = [0, 6, 12, 18]
MONTH_TICKS = list(range(1, 13))


def hourly_png(hourly: pd.DataFrame):
    cities = sorted(hourly["city"].unique())
    figure, axes = panel_grid(len(cities))
    for axis, city in zip(axes, cities):
        for season in [season for season in SEASONS if season in set(hourly["season"])]:
            rows = hourly[(hourly["city"] == city) & (hourly["season"] == season)]
            rows = rows.sort_values("hr")
            axis.plot(rows["hr"], rows["mean_temp_f"], color=SEASON_COLORS[season], label=season)
        axis.set_title(city)
        axis.set_xticks(HOUR_TICKS)
    title = "Hourly temperature cycle by city and season (routine FM-15 reports)"
    finish_panels(figure, axes, title, "Hour of day (local standard time)", "Mean temperature (°F)")
    return figure


def hourly_html(hourly: pd.DataFrame):
    return px.line(
        hourly.sort_values(["city", "season", "hr"]),
        x="hr",
        y="mean_temp_f",
        color="season",
        facet_col="city",
        facet_col_wrap=PANEL_COLUMNS,
        color_discrete_map=SEASON_COLORS,
        category_orders={"season": SEASONS, "city": sorted(hourly["city"].unique())},
        labels={"hr": "Hour", "mean_temp_f": "Mean temperature (°F)", "season": "Season"},
        title="Hourly temperature cycle by city and season (routine FM-15 reports)",
    )


def climatology_png(monthly: pd.DataFrame):
    figure, axis = plt.subplots(figsize=(10, 5))
    sns.lineplot(data=monthly, x="mo", y="mean_tavg_f", hue="city", marker="o", ax=axis)
    axis.set_xticks(MONTH_TICKS)
    axis.set_xlabel("Month")
    axis.set_ylabel("Mean daily temperature (°F)")
    axis.set_title("Seasonal temperature cycle by city, 2010-2025")
    axis.legend(title="", loc="center left", bbox_to_anchor=(1.0, 0.5))
    return figure


def climatology_html(monthly: pd.DataFrame):
    figure = px.line(
        monthly.sort_values(["city", "mo"]),
        x="mo",
        y="mean_tavg_f",
        color="city",
        markers=True,
        hover_data=["mean_tmax_f", "mean_tmin_f"],
        labels={"mo": "Month", "mean_tavg_f": "Mean daily temperature (°F)", "city": ""},
        title="Seasonal temperature cycle by city, 2010-2025",
    )
    figure.update_xaxes(tickvals=MONTH_TICKS)
    return figure


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(__doc__.splitlines()[0], argv)
    apply_style()
    hourly = load_result(args.results_dir, "q4_hourly_profile")
    monthly = load_result(args.results_dir, "q4_monthly_climatology")
    save_png(hourly_png(hourly), args.figures_dir, "q4_hourly_cycle")
    save_html(hourly_html(hourly), args.figures_dir, "q4_hourly_cycle")
    save_png(climatology_png(monthly), args.figures_dir, "q4_monthly_climatology")
    save_html(climatology_html(monthly), args.figures_dir, "q4_monthly_climatology")


if __name__ == "__main__":
    main()
