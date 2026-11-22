from datetime import date

import pytest

pytest.importorskip("pyspark")

from pyspark.sql import functions as F  # noqa: E402

from lcdweather.ml.classification_features import (  # noqa: E402
    CLASSIFICATION_FEATURES,
    build_classification_dataset,
)
from lcdweather.ml.regression_features import (  # noqa: E402
    REGRESSION_FEATURES,
    build_regression_dataset,
)
from lcdweather.ml.settings import SplitYears  # noqa: E402
from lcdweather.ml.splits import split_by_target_year  # noqa: E402
from lcdweather.ml.synthetic import synthetic_tables  # noqa: E402
from lcdweather.ml.synthetic_weather import SyntheticCity, SyntheticSpec  # noqa: E402

SPEC = SyntheticSpec(
    cities=(
        SyntheticCity("KAAA", "Alpha", 60.0, 15.0, 0.4),
        SyntheticCity("KBBB", "Beta", 45.0, 25.0, 0.3),
    ),
    years=(2021, 2022),
    days_of_year=tuple(range(350, 366)),
    hours=(0, 6, 12, 18, 23),
)
CUTOFF = date(2021, 12, 25)
POISON = 9999.0


@pytest.fixture(scope="module")
def tables(spark):
    hourly, daily = synthetic_tables(spark, SPEC)
    return hourly.cache(), daily.cache()


def _poison_after(frame, cutoff, columns):
    """Overwrite every value observed after the cutoff day."""
    poisoned = frame
    for name in columns:
        value = F.when(F.col("obs_date") > F.lit(cutoff), F.lit(POISON)).otherwise(F.col(name))
        poisoned = poisoned.withColumn(name, value.cast(frame.schema[name].dataType))
    return poisoned


def _rows_up_to(dataset, cutoff, columns):
    rows = dataset.where(F.col("obs_date") <= F.lit(cutoff)).select(
        "city_code", "obs_date", *columns
    )
    return sorted(rows.collect(), key=lambda row: (row["city_code"], row["obs_date"]))


@pytest.mark.parametrize(
    "build, features",
    [
        (build_regression_dataset, REGRESSION_FEATURES),
        (build_classification_dataset, CLASSIFICATION_FEATURES),
    ],
)
def test_features_never_depend_on_later_days(tables, build, features):
    hourly, daily = tables
    daily_values = ["tmax_f", "tmin_f", "tavg_f", "dep_f", "prcp_in"]
    hourly_values = [
        "temp_f",
        "dewpt_f",
        "rh_pct",
        "wind_speed_mph",
        "station_pressure_hpa",
        "precip_in",
    ]
    columns = list(features.numeric) + ["month"]

    clean = _rows_up_to(build(daily, hourly), CUTOFF, columns)
    poisoned = _rows_up_to(
        build(
            _poison_after(daily, CUTOFF, daily_values),
            _poison_after(hourly, CUTOFF, hourly_values),
        ),
        CUTOFF,
        columns,
    )

    assert len(clean) == 2 * 10
    assert clean == poisoned


def test_regression_label_is_the_next_days_maximum(tables):
    hourly, daily = tables
    tmax = {(row["city_code"], row["obs_date"]): row["tmax_f"] for row in daily.collect()}

    rows = build_regression_dataset(daily, hourly).collect()

    assert rows
    for row in rows:
        assert (row["target_date"] - row["obs_date"]).days == 1
        assert row["label"] == pytest.approx(tmax[(row["city_code"], row["target_date"])])
        assert row["pred_persistence"] == pytest.approx(tmax[(row["city_code"], row["obs_date"])])
        assert row["tmax_f_lag1"] == tmax.get(
            (row["city_code"], date.fromordinal(row["obs_date"].toordinal() - 1))
        )


def test_last_day_before_a_gap_has_no_label(tables):
    hourly, daily = tables

    dates = {row["obs_date"] for row in build_regression_dataset(daily, hourly).collect()}

    # 2021-12-31 is the last generated day of 2021; the next one is 2022-12-16.
    assert date(2021, 12, 30) in dates
    assert date(2021, 12, 31) not in dates


def test_classification_label_is_next_day_measurable_precipitation(tables):
    hourly, daily = tables
    precip = {(row["city_code"], row["obs_date"]): row["prcp_in"] for row in daily.collect()}

    rows = build_classification_dataset(daily, hourly).collect()

    assert {row["label"] for row in rows} == {0.0, 1.0}
    for row in rows:
        assert row["label"] == float(precip[(row["city_code"], row["target_date"])] >= 0.01)
        assert row["p_persistence"] == float(precip[(row["city_code"], row["obs_date"])] >= 0.01)


def test_trace_precipitation_is_not_a_wet_day(spark):
    schema = (
        "city_code string, city string, obs_date string, tmax_f double, tmin_f double, "
        "tavg_f double, dep_f double, prcp_in double"
    )
    daily = spark.createDataFrame(
        [
            ("KAAA", "Alpha", "2020-03-01", 50.0, 40.0, 45.0, 0.0, 0.0),
            ("KAAA", "Alpha", "2020-03-02", 50.0, 40.0, 45.0, 0.0, 0.005),
            ("KAAA", "Alpha", "2020-03-03", 50.0, 40.0, 45.0, 0.0, 0.01),
            ("KAAA", "Alpha", "2020-03-04", 50.0, 40.0, 45.0, 0.0, None),
        ],
        schema,
    ).withColumn("obs_date", F.to_date("obs_date"))
    hourly, _ = synthetic_tables(spark, SPEC)

    rows = build_classification_dataset(daily, hourly.limit(0)).orderBy("obs_date").collect()

    # 1 March -> trace on the 2nd (dry); 2 March -> 0.01 in on the 3rd (wet);
    # 3 March has an unknown next day and is dropped.
    assert [(row["obs_date"], row["label"]) for row in rows] == [
        (date(2020, 3, 1), 0.0),
        (date(2020, 3, 2), 1.0),
    ]


def test_split_is_keyed_on_the_predicted_day(tables):
    hourly, daily = tables
    dataset = build_regression_dataset(daily, hourly)

    splits = split_by_target_year(
        dataset, SplitYears(train_end=2021, validation_end=2022, test_end=2023)
    )

    train_targets = [row["target_date"] for row in splits.train.collect()]
    validation_targets = [row["target_date"] for row in splits.validation.collect()]
    assert max(train_targets) == date(2021, 12, 31)
    assert min(validation_targets) >= date(2022, 1, 1)
    assert splits.test.count() == 0
    assert len(train_targets) + len(validation_targets) == dataset.count()
