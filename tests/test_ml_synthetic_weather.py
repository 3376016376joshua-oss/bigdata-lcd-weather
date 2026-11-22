from lcdweather.ingest.contract import REPORT_ROUTINE, REPORT_SPECIAL
from lcdweather.ml.synthetic_weather import (
    SyntheticCity,
    SyntheticSpec,
    generate_rows,
)

SPEC = SyntheticSpec(
    cities=(SyntheticCity("KAAA", "Alpha", 60.0, 15.0, 0.5),),
    years=(2020, 2021),
    days_of_year=(1, 2, 3, 4),
    hours=(0, 12),
)


def test_generation_is_deterministic():
    assert generate_rows(SPEC) == generate_rows(SPEC)


def test_one_daily_row_per_city_day_and_routine_reports_per_hour():
    hourly, daily = generate_rows(SPEC)

    assert len(daily) == 8
    routine = [row for row in hourly if row[4] == REPORT_ROUTINE]
    assert len(routine) == 8 * 2


def test_special_reports_only_on_wet_days():
    hourly, daily = generate_rows(SPEC)

    wet_days = {row[2] for row in daily if row[7] > 0}
    special_days = {row[3] for row in hourly if row[4] == REPORT_SPECIAL}
    assert special_days == wet_days
    assert wet_days, "the fixture should contain at least one wet day"
