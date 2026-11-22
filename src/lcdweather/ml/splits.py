"""Time-based train / validation / test splits keyed on the predicted day."""

from __future__ import annotations

from dataclasses import dataclass

from pyspark.sql import DataFrame
from pyspark.sql import functions as F

from lcdweather.ml.settings import DEFAULT_SPLIT_YEARS, SplitYears

TARGET_DATE_COL = "target_date"


@dataclass(frozen=True)
class Splits:
    train: DataFrame
    validation: DataFrame
    test: DataFrame


def split_by_target_year(dataset: DataFrame, years: SplitYears = DEFAULT_SPLIT_YEARS) -> Splits:
    """Split on the year of the day being predicted.

    Features always precede the target day, so keying the split on the target
    keeps every validation/test label strictly after all training labels.
    """
    target_year = F.year(F.col(TARGET_DATE_COL))
    return Splits(
        train=dataset.where(target_year <= years.train_end),
        validation=dataset.where(
            (target_year > years.train_end) & (target_year <= years.validation_end)
        ),
        test=dataset.where((target_year > years.validation_end) & (target_year <= years.test_end)),
    )
