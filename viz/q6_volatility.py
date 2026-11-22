"""Question 6 figures: temperature volatility, humidity and special reports.

Reads q6_city_volatility.csv, q6_special_reports_by_day_type.csv and
q6_special_reports_around_storms.csv. Writes q6_city_volatility,
q6_special_reports_wet_vs_dry and q6_special_reports_around_storms as PNG and HTML.
"""

from __future__ import annotations

from collections.abc import Sequence

import matplotlib.pyplot as plt
import pandas as pd
import plotly.express as px
import seaborn as sns
from analysis_plotting import (
    COLD_COLOR,
    apply_style,
    load_result,
    parse_args,
    save_html,
    save_png,
)

METRICS = {
    "tavg_change_sd_f": "Day-to-day change of daily mean, std dev (°F)",
    "mean_daily_range_f": "Mean daily temperature range (°F)",
    "mean_rh_pct": "Mean relative humidity (%)",
}
DAY_TYPE_LABELS = {"dry": "Dry day", "wet": "Wet day"}
DAY_TYPE_COLORS = {"Dry day": "#d8b365", "Wet day": COLD_COLOR}


def volatility_png(volatility: pd.DataFrame):
    figure, axes = plt.subplots(1, len(METRICS), figsize=(15, 4.5), sharey=True)
    ordered = volatility.sort_values("tavg_change_sd_f")
    for axis, (column, label) in zip(axes, METRICS.items()):
        axis.barh(ordered["city"], ordered[column], color="#5e3c99")
        axis.set_xlabel(label)
        axis.grid(axis="y", visible=False)
    figure.suptitle("Temperature volatility, daily range and humidity by city, 2010-2025")
    figure.tight_layout()
    return figure


def volatility_html(volatility: pd.DataFrame):
    melted = volatility.melt(id_vars=["city"], value_vars=list(METRICS), var_name="metric")
    figure = px.bar(
        melted.assign(metric=melted["metric"].map(METRICS)),
        x="value",
        y="city",
        facet_col="metric",
        orientation="h",
        category_orders={"city": list(volatility.sort_values("tavg_change_sd_f")["city"])[::-1]},
        labels={"value": "", "city": ""},
        title="Temperature volatility, daily range and humidity by city, 2010-2025",
    )
    figure.update_xaxes(matches=None)
    return figure


def wet_vs_dry_png(by_day_type: pd.DataFrame):
    figure, axis = plt.subplots(figsize=(10, 4.5))
    sns.barplot(
        data=by_day_type,
        x="city",
        y="mean_special_reports_per_day",
        hue="day_type",
        palette=DAY_TYPE_COLORS,
        ax=axis,
    )
    axis.tick_params(axis="x", rotation=45)
    axis.set_xlabel("")
    axis.set_ylabel("Special reports (FM-16) per day")
    axis.set_title("Special weather reports on wet and dry days")
    axis.legend(title="")
    return figure


def wet_vs_dry_html(by_day_type: pd.DataFrame):
    return px.bar(
        by_day_type,
        x="city",
        y="mean_special_reports_per_day",
        color="day_type",
        barmode="group",
        color_discrete_map=DAY_TYPE_COLORS,
        hover_data=["n_days", "pct_days_with_special", "mean_pressure_range_hpa"],
        labels={
            "city": "",
            "mean_special_reports_per_day": "Special reports per day",
            "day_type": "",
        },
        title="Special weather reports (FM-16) on wet and dry days",
    )


def around_storms_png(around: pd.DataFrame):
    figure, axis = plt.subplots(figsize=(10, 5))
    sns.lineplot(
        data=around, x="day_offset", y="mean_special_reports", hue="city", marker="o", ax=axis
    )
    axis.axvline(0, color="black", linewidth=0.8, linestyle="--")
    axis.set_xlabel("Days from the storm day")
    axis.set_ylabel("Special reports (FM-16) per day")
    axis.set_title("Special reports around the five wettest days of each city")
    axis.legend(title="", loc="center left", bbox_to_anchor=(1.0, 0.5))
    return figure


def around_storms_html(around: pd.DataFrame):
    return px.line(
        around.sort_values(["city", "day_offset"]),
        x="day_offset",
        y="mean_special_reports",
        color="city",
        markers=True,
        hover_data=["mean_prcp_in", "city_mean_special_reports"],
        labels={
            "day_offset": "Days from the storm day",
            "mean_special_reports": "Special reports per day",
            "city": "",
        },
        title="Special reports (FM-16) around the five wettest days of each city",
    )


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(__doc__.splitlines()[0], argv)
    apply_style()
    volatility = load_result(args.results_dir, "q6_city_volatility")
    by_day_type = load_result(args.results_dir, "q6_special_reports_by_day_type")
    by_day_type = by_day_type.assign(day_type=by_day_type["day_type"].map(DAY_TYPE_LABELS))
    around = load_result(args.results_dir, "q6_special_reports_around_storms")
    save_png(volatility_png(volatility), args.figures_dir, "q6_city_volatility")
    save_html(volatility_html(volatility), args.figures_dir, "q6_city_volatility")
    save_png(wet_vs_dry_png(by_day_type), args.figures_dir, "q6_special_reports_wet_vs_dry")
    save_html(wet_vs_dry_html(by_day_type), args.figures_dir, "q6_special_reports_wet_vs_dry")
    save_png(around_storms_png(around), args.figures_dir, "q6_special_reports_around_storms")
    save_html(around_storms_html(around), args.figures_dir, "q6_special_reports_around_storms")


if __name__ == "__main__":
    main()
