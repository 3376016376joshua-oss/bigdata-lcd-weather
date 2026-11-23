"""Question 5 figures: precipitation against normal, dry spells and heavy rain.

Reads q5_monthly_precip_vs_normal.csv, q5_dry_spells.csv and
q5_heaviest_rain_days.csv. Writes q5_precip_actual_vs_normal, q5_longest_dry_spells
and q5_heaviest_rain_days as PNG and HTML.
"""

from __future__ import annotations

from collections.abc import Sequence

import matplotlib.pyplot as plt
import pandas as pd
import plotly.express as px
import seaborn as sns
from analysis_plotting import (
    COLD_COLOR,
    NEUTRAL_COLOR,
    PANEL_COLUMNS,
    apply_style,
    finish_panels,
    load_result,
    panel_grid,
    parse_args,
    save_html,
    save_png,
)

MONTH_TICKS = [1, 4, 7, 10]
SERIES_LABELS = {"actual_in": "Actual", "normal_in": "Normal"}
SERIES_COLORS = {"Actual": COLD_COLOR, "Normal": NEUTRAL_COLOR}


def calendar_month_means(monthly: pd.DataFrame) -> pd.DataFrame:
    """Mean actual and normal precipitation per city and calendar month.

    The normal is the station normal of the calendar month; only a calendar month that
    has none in any year falls back to its 2010-2025 mean.
    """
    prepared = monthly.assign(
        actual_in=monthly["total_prcp_in"],
        normal_in=monthly["normal_prcp_in"],
        period_mean_in=monthly["period_mean_prcp_in"],
    )
    columns = ["actual_in", "normal_in", "period_mean_in"]
    means = prepared.groupby(["city", "mo"], as_index=False)[columns].mean()
    means["normal_in"] = means["normal_in"].fillna(means["period_mean_in"])
    return means.drop(columns="period_mean_in")


def actual_vs_normal_png(means: pd.DataFrame):
    cities = sorted(means["city"].unique())
    figure, axes = panel_grid(len(cities))
    for axis, city in zip(axes, cities):
        rows = means[means["city"] == city].sort_values("mo")
        axis.bar(rows["mo"], rows["actual_in"], color=COLD_COLOR, label="Actual")
        axis.plot(
            rows["mo"], rows["normal_in"], color="black", marker="o", markersize=3, label="Normal"
        )
        axis.set_title(city)
        axis.set_xticks(MONTH_TICKS)
    title = "Monthly precipitation, actual 2010-2025 against normal"
    finish_panels(figure, axes, title, "Month", "Mean monthly precipitation (in)")
    return figure


def actual_vs_normal_html(means: pd.DataFrame):
    melted = means.melt(
        id_vars=["city", "mo"],
        value_vars=list(SERIES_LABELS),
        var_name="series",
        value_name="inches",
    )
    return px.bar(
        melted.assign(series=melted["series"].map(SERIES_LABELS)),
        x="mo",
        y="inches",
        color="series",
        barmode="group",
        facet_col="city",
        facet_col_wrap=PANEL_COLUMNS,
        color_discrete_map=SERIES_COLORS,
        category_orders={"city": sorted(means["city"].unique())},
        labels={"mo": "Month", "inches": "Precipitation (in)", "series": ""},
        title="Monthly precipitation, actual 2010-2025 against normal",
    )


def longest_spells(spells: pd.DataFrame) -> pd.DataFrame:
    longest = spells[spells["spell_rank"] == 1].sort_values("length_days")
    return longest.assign(dates=longest["start_date"] + " to " + longest["end_date"])


def dry_spells_png(longest: pd.DataFrame):
    figure, axis = plt.subplots(figsize=(9, 4.5))
    bars = axis.barh(longest["city"], longest["length_days"], color="#d8b365")
    axis.bar_label(bars, labels=list(longest["dates"]), padding=3, fontsize="x-small")
    axis.margins(x=0.35)
    axis.grid(axis="y", visible=False)
    axis.set_xlabel("Consecutive dry days (less than 0.01 in)")
    axis.set_title("Longest dry spell by city, 2010-2025")
    return figure


def dry_spells_html(spells: pd.DataFrame):
    labelled = spells.assign(rank=spells["spell_rank"].astype(str))
    return px.bar(
        labelled.sort_values(["city", "spell_rank"]),
        x="city",
        y="length_days",
        color="rank",
        barmode="group",
        hover_data=["start_date", "end_date"],
        labels={"city": "", "length_days": "Consecutive dry days", "rank": "Rank"},
        title="Five longest dry spells by city, 2010-2025",
    )


def rain_days_png(rain: pd.DataFrame):
    figure, axis = plt.subplots(figsize=(10, 4.5))
    sns.stripplot(data=rain, x="city", y="prcp_in", color=COLD_COLOR, size=6, ax=axis)
    axis.tick_params(axis="x", rotation=45)
    axis.set_xlabel("")
    axis.set_ylabel("Daily precipitation (in)")
    axis.set_title("Ten wettest days by city, 2010-2025")
    return figure


def rain_days_html(rain: pd.DataFrame):
    return px.scatter(
        rain,
        x="city",
        y="prcp_in",
        color="season",
        hover_data=["obs_date", "city_rank", "overall_rank"],
        labels={"city": "", "prcp_in": "Daily precipitation (in)", "season": "Season"},
        title="Ten wettest days by city, 2010-2025",
    )


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(__doc__.splitlines()[0], argv)
    apply_style()
    means = calendar_month_means(load_result(args.results_dir, "q5_monthly_precip_vs_normal"))
    spells = load_result(args.results_dir, "q5_dry_spells")
    rain = load_result(args.results_dir, "q5_heaviest_rain_days").sort_values("city")
    save_png(actual_vs_normal_png(means), args.figures_dir, "q5_precip_actual_vs_normal")
    save_html(actual_vs_normal_html(means), args.figures_dir, "q5_precip_actual_vs_normal")
    save_png(dry_spells_png(longest_spells(spells)), args.figures_dir, "q5_longest_dry_spells")
    save_html(dry_spells_html(spells), args.figures_dir, "q5_longest_dry_spells")
    save_png(rain_days_png(rain), args.figures_dir, "q5_heaviest_rain_days")
    save_html(rain_days_html(rain), args.figures_dir, "q5_heaviest_rain_days")


if __name__ == "__main__":
    main()
