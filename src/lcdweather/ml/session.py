"""SparkSession construction for the Phase 5 jobs and their tests."""

from __future__ import annotations

import os
import sys

from pyspark.sql import SparkSession

from lcdweather.ingest.session import SESSION_TIME_ZONE

LOCAL_MASTER_PREFIX = "local"
WORKER_PYTHON_ENV = "PYSPARK_PYTHON"


def build_session(
    app_name: str,
    master: str | None = None,
    hive: bool = False,
    shuffle_partitions: int | None = None,
) -> SparkSession:
    """Create (or reuse) a session; master is left to spark-submit when None."""
    # obs_ts was written in a UTC session; reading it in another zone would shift its hour.
    builder = SparkSession.builder.appName(app_name).config(
        "spark.sql.session.timeZone", SESSION_TIME_ZONE
    )
    if master:
        builder = builder.master(master)
        if master.startswith(LOCAL_MASTER_PREFIX):
            # Local workers share this machine, so they must use the driver's
            # interpreter rather than whichever python3 is first on PATH.
            os.environ.setdefault(WORKER_PYTHON_ENV, sys.executable)
    if shuffle_partitions:
        builder = builder.config("spark.sql.shuffle.partitions", shuffle_partitions)
    if hive:
        builder = builder.enableHiveSupport()
    return builder.getOrCreate()
