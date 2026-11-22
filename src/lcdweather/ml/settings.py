"""Constants and environment-driven defaults for the Phase 5 jobs."""

from __future__ import annotations

from dataclasses import dataclass

HOURLY_TABLE = "lcd_hourly"
DAILY_TABLE = "lcd_daily"

ROUTINE_REPORT_TYPE = "FM-15"
WET_DAY_THRESHOLD_IN = 0.01
RANDOM_SEED = 42
LABEL_COL = "label"
# The modelling tables are tiny (about 58k city-days); a few partitions avoid
# scheduling hundreds of near-empty tasks for every tree-boosting iteration.
MODEL_DATA_PARTITIONS = 8


@dataclass(frozen=True)
class SplitYears:
    """Last calendar year (inclusive) of each time-based split."""

    train_end: int = 2021
    validation_end: int = 2023
    test_end: int = 2025


DEFAULT_SPLIT_YEARS = SplitYears()
