"""Spark expressions that turn the quoted text of LCD v2 into typed values.

A cell can be blank, a number, a number with a one-letter flag (``0.805s`` suspect,
``4.023V`` variable), ``T`` for a trace amount, or a marker with no usable value
(``*`` erroneous, ``M``, ``None``, ``VRB`` wind direction). Anything that is not a number
becomes null rather than failing the job.
"""

from __future__ import annotations

from pyspark.sql import Column
from pyspark.sql import functions as F

NUMBER_PATTERN = r"^\s*([-+]?(?:\d+\.?\d*|\.\d+))\s*[A-Za-z]?\s*$"
TRACE_PATTERN = r"^\s*T\s*[A-Za-z]?\s*$"
# Lowest reported layer whose amount is 00-08 oktas or 09 (sky obscured). Layers coded 10
# (partly obscured, amount unknown) and bare cloud heights carry no amount and are skipped.
SKY_LAYER_OKTA_PATTERN = r"(?:^|\s)[A-Z0-9]*:(0\d)(?:\s|$)"
CLOCK_PATTERN = r"^\d{4}$"
RAW_TIMESTAMP_FORMAT = "yyyy-MM-dd'T'HH:mm:ss"
TRACE_AMOUNT = 0.0


def number(text: Column) -> Column:
    """The numeric value of a cell, ignoring a trailing flag letter; null when there is none."""
    digits = F.regexp_extract(text, NUMBER_PATTERN, 1)
    return F.when(digits != "", digits.cast("double"))


def whole_number(text: Column) -> Column:
    """Like ``number`` for cells that hold integers written as ``270`` or ``270.0``."""
    return number(text).cast("int")


def is_trace(text: Column) -> Column:
    """Whether a precipitation or snow cell holds ``T``; false for blank cells."""
    return F.coalesce(text.rlike(TRACE_PATTERN), F.lit(False))


def amount(text: Column) -> Column:
    """A precipitation or snow amount, with a trace counted as 0.0."""
    return F.when(is_trace(text), F.lit(TRACE_AMOUNT)).otherwise(number(text))


def sky_cover_okta(sky_conditions: Column) -> Column:
    """Cover of the lowest cloud layer in oktas (0-8, 9 = sky obscured); null when unknown."""
    okta = F.regexp_extract(sky_conditions, SKY_LAYER_OKTA_PATTERN, 1)
    return F.when(okta != "", okta.cast("int"))


def clock_time(text: Column) -> Column:
    """A ``HHmm`` local standard time such as sunrise ``0720``; null when malformed."""
    trimmed = F.trim(text)
    return F.when(trimmed.rlike(CLOCK_PATTERN), trimmed)


def text_or_null(text: Column) -> Column:
    """The trimmed cell, with blank turned into null."""
    trimmed = F.trim(text)
    return F.when(trimmed != "", trimmed)


def timestamp(text: Column) -> Column:
    """The ``DATE`` cell as a timestamp; null when it is not ``YYYY-MM-DDTHH:mm:ss``."""
    return F.to_timestamp(F.trim(text), RAW_TIMESTAMP_FORMAT)
