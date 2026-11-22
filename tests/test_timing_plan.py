import pytest

from lcdweather.timing.plan import YearWindow, year_windows


def test_default_windows_cover_1_4_8_and_16_years_ending_in_2025():
    windows = year_windows()

    assert [(w.start, w.end) for w in windows] == [
        (2025, 2025),
        (2022, 2025),
        (2018, 2025),
        (2010, 2025),
    ]
    assert [w.n_years for w in windows] == [1, 4, 8, 16]


def test_windows_run_smallest_first_whatever_the_requested_order():
    windows = year_windows(sizes=[8, 1, 8], first_year=2010, last_year=2017)

    assert windows == [YearWindow(2017, 2017), YearWindow(2010, 2017)]


def test_window_larger_than_the_available_period_is_rejected():
    with pytest.raises(ValueError, match="does not fit"):
        year_windows(sizes=[17])


def test_year_window_lists_its_years():
    assert YearWindow(2023, 2025).years == [2023, 2024, 2025]
