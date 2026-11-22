"""Modelling constants of the Phase 5 jobs; table and column names live in ingest.contract."""

from __future__ import annotations

from dataclasses import dataclass

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
