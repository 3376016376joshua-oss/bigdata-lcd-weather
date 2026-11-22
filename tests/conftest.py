"""Shared pytest fixtures: paths to the LCD sample and a local SparkSession.

Spark tests need pyspark and a Java runtime. Without them they are skipped, unless
``LCD_REQUIRE_SPARK=1`` (set in CI) turns the skip into a failure so they cannot be lost.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
LCD_SAMPLE_NAME = "LCD_USW00094728_2014_sample.csv"
ENV_REQUIRE_SPARK = "LCD_REQUIRE_SPARK"
ENV_PYSPARK_PYTHON = "PYSPARK_PYTHON"
SPARK_MASTER = "local[2]"
SPARK_APP_NAME = "lcdweather-tests"
JAVA_CHECK_TIMEOUT_SECONDS = 60


def _java_command() -> str:
    java_home = os.environ.get("JAVA_HOME")
    return str(Path(java_home) / "bin" / "java") if java_home else "java"


def _why_spark_is_unavailable() -> str | None:
    """A reason Spark cannot start here, or None when pyspark and Java are both usable."""
    try:
        import pyspark  # noqa: F401
    except ImportError as error:
        return f"pyspark is not installed ({error})"
    try:
        # macOS ships a `java` stub that exists but exits non-zero when no JDK is installed.
        subprocess.run(
            [_java_command(), "-version"],
            check=True,
            capture_output=True,
            timeout=JAVA_CHECK_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.SubprocessError) as error:
        return f"no working Java runtime ({error})"
    return None


@pytest.fixture(scope="session")
def fixtures_dir() -> Path:
    return FIXTURES_DIR


@pytest.fixture(scope="session")
def lcd_sample_path() -> Path:
    """Five days of Central Park reports on the real 125-column LCD v2 header."""
    return FIXTURES_DIR / LCD_SAMPLE_NAME


@pytest.fixture(scope="session")
def spark(tmp_path_factory):
    """One local SparkSession for the whole test run."""
    reason = _why_spark_is_unavailable()
    if reason is not None:
        if os.environ.get(ENV_REQUIRE_SPARK) == "1":
            pytest.fail(f"{ENV_REQUIRE_SPARK}=1 but {reason}")
        pytest.skip(reason)
    from pyspark.sql import SparkSession

    with pytest.MonkeyPatch.context() as environment:
        # Spark starts its Python workers with `python3` from PATH unless told otherwise, and
        # a worker on another Python version than the tests cannot run.
        environment.setenv(ENV_PYSPARK_PYTHON, sys.executable)
        session = (
            SparkSession.builder.master(SPARK_MASTER)
            .appName(SPARK_APP_NAME)
            .config("spark.ui.enabled", "false")
            .config("spark.driver.host", "127.0.0.1")
            .config("spark.driver.bindAddress", "127.0.0.1")
            .config("spark.sql.shuffle.partitions", "2")
            .config("spark.default.parallelism", "2")
            .config("spark.sql.session.timeZone", "UTC")
            .config("spark.sql.warehouse.dir", str(tmp_path_factory.mktemp("spark-warehouse")))
            .getOrCreate()
        )
        yield session
        session.stop()
