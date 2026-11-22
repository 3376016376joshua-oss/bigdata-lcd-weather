"""Question 3 figures: balance of warm against cold extremes and its trend.

Reads q3_balance_by_year.csv and q3_balance_trend.csv. Writes q3_balance_by_year and
q3_balance_trend_by_city as PNG and HTML.
"""

from __future__ import annotations

from collections.abc import Sequence

import matplotlib.pyplot as plt
import pandas as pd
import plotly.graph_objects as go
from analysis_plotting import (
    ALL_CITIES_CODE,
    COLD_COLOR,
    WARM_COLOR,
    apply_style,
    load_result,
    parse_args,
    save_html,
    save_png,
)

YEARS_PER_DECADE = 10


def overall_series(by_year: pd.DataFrame, trend: pd.DataFrame) -> pd.DataFrame:
    """Yearly balance of all cities together with the fitted trend line."""
    overall = by_year[by_year["city_code"] == ALL_CITIES_CODE].sort_values("yr")
    fit = trend[trend["city_code"] == ALL_CITIES_CODE].iloc[0]
    slope_per_year = fit["balance_slope_per_decade"] / YEARS_PER_DECADE
    fitted = fit["mean_warm_minus_cold"] + slope_per_year * (overall["yr"] - fit["mean_yr"])
    return overall.assign(fitted=fitted, slope_per_decade=fit["balance_slope_per_decade"])


def sign_colors(values: pd.Series) -> list[str]:
    return [WARM_COLOR if value >= 0 else COLD_COLOR for value in values]


def balance_title(overall: pd.DataFrame) -> str:
    slope = overall["slope_per_decade"].iloc[0]
    return f"Warm minus cold extreme days, all cities (trend {slope:+.1f} days per decade)"


def balance_png(overall: pd.DataFrame):
    figure, axis = plt.subplots(figsize=(10, 4.5))
    axis.bar(
        overall["yr"], overall["warm_minus_cold"], color=sign_colors(overall["warm_minus_cold"])
    )
    axis.plot(overall["yr"], overall["fitted"], color="black", linestyle="--", label="Linear trend")
    axis.axhline(0, color="black", linewidth=0.8)
    axis.set_xticks(list(overall["yr"]))
    axis.tick_params(axis="x", rotation=45)
    axis.set_ylabel("Warm minus cold extreme days")
    axis.set_title(balance_title(overall))
    axis.legend(loc="best")
    return figure


def balance_html(overall: pd.DataFrame):
    figure = go.Figure()
    figure.add_bar(
        x=overall["yr"],
        y=overall["warm_minus_cold"],
        name="Warm minus cold",
        marker_color=sign_colors(overall["warm_minus_cold"]),
        customdata=overall[["warm_extreme_days", "cold_extreme_days"]].to_numpy(),
        hovertemplate="%{x}: %{y} (warm %{customdata[0]}, cold %{customdata[1]})",
    )
    figure.add_scatter(
        x=overall["yr"],
        y=overall["fitted"],
        name="Linear trend",
        mode="lines",
        line={"color": "black", "dash": "dash"},
    )
    figure.update_layout(
        title=balance_title(overall), xaxis_title="Year", yaxis_title="Warm minus cold extreme days"
    )
    return figure


def city_trends(trend: pd.DataFrame) -> pd.DataFrame:
    cities = trend[trend["city_code"] != ALL_CITIES_CODE]
    return cities.sort_values("balance_slope_per_decade")


def trend_png(cities: pd.DataFrame):
    figure, axis = plt.subplots(figsize=(8, 4.5))
    axis.barh(
        cities["city"],
        cities["balance_slope_per_decade"],
        color=sign_colors(cities["balance_slope_per_decade"]),
    )
    axis.axvline(0, color="black", linewidth=0.8)
    axis.grid(axis="y", visible=False)
    axis.set_xlabel("Trend of warm minus cold extreme days (days per decade)")
    axis.set_title("Change in the warm/cold balance by city, 2010-2025")
    return figure


def trend_html(cities: pd.DataFrame):
    figure = go.Figure(
        go.Bar(
            x=cities["balance_slope_per_decade"],
            y=cities["city"],
            orientation="h",
            marker_color=sign_colors(cities["balance_slope_per_decade"]),
            customdata=cities[["warm_extreme_days", "cold_extreme_days"]].to_numpy(),
            hovertemplate="%{y}: %{x:+.1f} per decade (warm %{customdata[0]}, "
            "cold %{customdata[1]})<extra></extra>",
        )
    )
    figure.update_layout(
        title="Change in the warm/cold balance by city, 2010-2025",
        xaxis_title="Trend of warm minus cold extreme days (days per decade)",
    )
    return figure


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(__doc__.splitlines()[0], argv)
    apply_style()
    trend = load_result(args.results_dir, "q3_balance_trend")
    overall = overall_series(load_result(args.results_dir, "q3_balance_by_year"), trend)
    cities = city_trends(trend)
    save_png(balance_png(overall), args.figures_dir, "q3_balance_by_year")
    save_html(balance_html(overall), args.figures_dir, "q3_balance_by_year")
    save_png(trend_png(cities), args.figures_dir, "q3_balance_trend_by_city")
    save_html(trend_html(cities), args.figures_dir, "q3_balance_trend_by_city")


if __name__ == "__main__":
    main()
