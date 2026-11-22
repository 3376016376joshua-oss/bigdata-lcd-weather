"""Phase 6 figure: run time of the ingest and analysis jobs against input size.

python viz/timing_scaling.py --results-dir results --figures-dir figures
"""

from __future__ import annotations

from collections.abc import Sequence

import matplotlib.pyplot as plt
from ml_plotting import SERIES_COLORS, parse_args, read_result, save_figure

JOB_COLORS = {"ingest": SERIES_COLORS[0], "analysis": SERIES_COLORS[1]}
JOB_LABELS = {"ingest": "Phase 2 ingest", "analysis": "Phase 4 analysis"}


def _job_label(job: str, slope) -> str:
    label = JOB_LABELS.get(job, job)
    if slope == slope and slope is not None:  # NaN-safe: a slope needs two sizes
        return f"{label} (log-log slope {slope:.2f})"
    return label


def plot_scaling(summary):
    """Linear and log-log views of median wall time vs input size, one line per job."""
    figure, (linear, loglog) = plt.subplots(1, 2, figsize=(10, 4))
    for job, rows in summary.groupby("job", sort=False):
        rows = rows.sort_values("input_gb")
        color = JOB_COLORS.get(job, SERIES_COLORS[2])
        label = _job_label(job, rows["loglog_slope"].iloc[0])
        for ax in (linear, loglog):
            ax.plot(
                rows["input_gb"],
                rows["median_wall_seconds"],
                marker="o",
                markersize=7,
                color=color,
                label=label,
            )
    linear.set(
        xlabel="Raw input size (GB)",
        ylabel="Median wall-clock time (s)",
        title="Run time vs input size",
    )
    linear.set_ylim(bottom=0)
    sizes = summary.drop_duplicates("n_years").sort_values("input_gb")
    ticks = [f"{gb:.2f}\n{int(years)} yr" for gb, years in zip(sizes["input_gb"], sizes["n_years"])]
    linear.set_xticks(sizes["input_gb"].tolist(), ticks)
    loglog.set(
        xscale="log",
        yscale="log",
        xlabel="Raw input size (GB, log)",
        ylabel="Median wall-clock time (s, log)",
        title="Log-log view (slope 1 = linear)",
    )
    linear.legend(loc="upper left")
    figure.tight_layout()
    return figure


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(__doc__, argv)
    summary = read_result(args.results_dir, "runtime_scaling_summary")
    save_figure(plot_scaling(summary), args.figures_dir, "timing_runtime_scaling")


if __name__ == "__main__":
    main()
