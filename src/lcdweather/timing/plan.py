"""Which year windows the scaling experiment runs on."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from lcdweather.config import DEFAULT_FIRST_YEAR, DEFAULT_LAST_YEAR

DEFAULT_SIZES = (1, 4, 8, 16)


@dataclass(frozen=True)
class YearWindow:
    start: int
    end: int

    @property
    def n_years(self) -> int:
        return self.end - self.start + 1

    @property
    def years(self) -> list[int]:
        return list(range(self.start, self.end + 1))


def year_windows(
    sizes: Sequence[int] = DEFAULT_SIZES,
    first_year: int = DEFAULT_FIRST_YEAR,
    last_year: int = DEFAULT_LAST_YEAR,
) -> list[YearWindow]:
    """Windows ending at `last_year`, smallest first.

    Running the largest window last leaves the tables and results of the full
    period in place once the experiment finishes.
    """
    available = last_year - first_year + 1
    windows = []
    for size in sorted(set(sizes)):
        if size < 1 or size > available:
            raise ValueError(f"Window of {size} years does not fit in {first_year}-{last_year}")
        windows.append(YearWindow(start=last_year - size + 1, end=last_year))
    return windows
