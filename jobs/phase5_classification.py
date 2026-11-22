"""Phase 5 / Question 8: predict whether the next day has measurable precipitation.

spark-submit --py-files dist/lcdweather.zip jobs/phase5_classification.py \
    --database wl3564_nyu_edu --results-dir hdfs:///user/wl3564_nyu_edu/lcd/results
"""

from __future__ import annotations

from collections.abc import Sequence

from lcdweather.ml.classification import run_classification
from lcdweather.ml.cli import build_parser, run_job


def main(argv: Sequence[str] | None = None) -> None:
    args = build_parser(__doc__).parse_args(argv)
    run_job(
        "lcd-phase5-classification",
        args,
        lambda tables: run_classification(tables.daily, tables.hourly, grid=args.grid),
    )


if __name__ == "__main__":
    main()
