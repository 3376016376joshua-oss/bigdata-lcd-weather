"""Phase 5 / Question 7: predict the next day's maximum temperature.

spark-submit --py-files lcdweather.zip jobs/phase5_regression.py \
    --database wl3564_nyu_edu --results-dir hdfs:///user/wl3564_nyu_edu/lcd/results
"""

from __future__ import annotations

from collections.abc import Sequence

from lcdweather.ml.cli import build_parser, run_job
from lcdweather.ml.regression import run_regression


def main(argv: Sequence[str] | None = None) -> None:
    args = build_parser(__doc__).parse_args(argv)
    run_job(
        "lcd-phase5-regression",
        args,
        lambda tables: run_regression(tables.daily, tables.hourly, grid=args.grid),
    )


if __name__ == "__main__":
    main()
