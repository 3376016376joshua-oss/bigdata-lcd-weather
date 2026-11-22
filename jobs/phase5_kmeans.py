"""Phase 5 / Question 4: cluster the ten cities into climate types with k-means.

spark-submit --py-files dist/lcdweather.zip jobs/phase5_kmeans.py \
    --database wl3564_nyu_edu --results-dir hdfs:///user/wl3564_nyu_edu/lcd/results
"""

from __future__ import annotations

from collections.abc import Sequence

from lcdweather.ml.cli import build_parser, run_job
from lcdweather.ml.clustering import DEFAULT_K_VALUES, run_kmeans


def main(argv: Sequence[str] | None = None) -> None:
    parser = build_parser(__doc__, with_grid=False)
    parser.add_argument(
        "--k-values",
        type=int,
        nargs="+",
        default=list(DEFAULT_K_VALUES),
        help="candidate cluster counts; the best silhouette is selected",
    )
    args = parser.parse_args(argv)
    run_job(
        "lcd-phase5-kmeans",
        args,
        lambda tables: run_kmeans(tables.daily, tables.hourly, args.k_values),
        year_round_synthetic=True,
    )


if __name__ == "__main__":
    main()
