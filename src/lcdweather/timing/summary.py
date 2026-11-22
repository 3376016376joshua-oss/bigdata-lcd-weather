"""How run time grows with input size: per-size medians and a log-log slope."""

from __future__ import annotations

import math
import statistics
from collections.abc import Sequence

BYTES_PER_GB = 1024**3
SUCCESS_EXIT_CODE = 0


def loglog_slope(points: Sequence[tuple[float, float]]) -> float | None:
    """Least-squares slope of log(y) on log(x); 1.0 means linear scaling."""
    usable = [(math.log(x), math.log(y)) for x, y in points if x > 0 and y > 0]
    if len(usable) < 2:
        return None
    mean_x = sum(x for x, _ in usable) / len(usable)
    mean_y = sum(y for _, y in usable) / len(usable)
    spread = sum((x - mean_x) ** 2 for x, _ in usable)
    if spread == 0:
        return None
    return sum((x - mean_x) * (y - mean_y) for x, y in usable) / spread


def _median_by_size(records: list[dict]) -> dict[int, dict]:
    by_size: dict[int, list[dict]] = {}
    for record in records:
        by_size.setdefault(int(record["n_years"]), []).append(record)
    return {
        n_years: {
            "wall_seconds": statistics.median(float(run["wall_seconds"]) for run in runs),
            "input_bytes": int(runs[0]["input_bytes"]),
            "runs": len(runs),
        }
        for n_years, runs in by_size.items()
    }


def summarize(records: Sequence[dict]) -> list[dict]:
    """Per job and window: median seconds, slowdown vs the smallest window, slope."""
    succeeded = [r for r in records if int(r["exit_code"]) == SUCCESS_EXIT_CODE]
    rows = []
    for job in sorted({record["job"] for record in succeeded}):
        sizes = _median_by_size([r for r in succeeded if r["job"] == job])
        ordered = sorted(sizes)
        baseline = sizes[ordered[0]]
        slope = loglog_slope([(sizes[n]["input_bytes"], sizes[n]["wall_seconds"]) for n in ordered])
        for n_years in ordered:
            size = sizes[n_years]
            gigabytes = size["input_bytes"] / BYTES_PER_GB
            rows.append(
                {
                    "job": job,
                    "n_years": n_years,
                    "runs": size["runs"],
                    "input_gb": gigabytes,
                    "median_wall_seconds": size["wall_seconds"],
                    "seconds_per_gb": size["wall_seconds"] / gigabytes if gigabytes else None,
                    "input_ratio": _ratio(size["input_bytes"], baseline["input_bytes"]),
                    "time_ratio": _ratio(size["wall_seconds"], baseline["wall_seconds"]),
                    "loglog_slope": slope,
                }
            )
    return rows


def _ratio(value: float, baseline: float) -> float | None:
    return value / baseline if baseline else None
