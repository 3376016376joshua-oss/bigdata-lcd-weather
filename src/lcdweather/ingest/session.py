"""Build the Spark session for the Phase 2 and 3 jobs."""

from __future__ import annotations

from pyspark.sql import SparkSession

# LCD times are local standard time with no daylight saving. A UTC session keeps every
# wall-clock value as written; a zone with daylight saving would shift or reject the
# hour skipped each spring.
SESSION_TIME_ZONE = "UTC"
LOCAL_MASTER = "local[*]"


def build_session(app_name: str, local: bool, warehouse_dir: str | None = None) -> SparkSession:
    """A Hive-enabled session on the cluster, or a self-contained local one for trials."""
    builder = SparkSession.builder.appName(app_name).config(
        "spark.sql.session.timeZone", SESSION_TIME_ZONE
    )
    if local:
        builder = builder.master(LOCAL_MASTER).config("spark.ui.enabled", "false")
        if warehouse_dir is not None:
            builder = builder.config("spark.sql.warehouse.dir", warehouse_dir)
    else:
        builder = builder.enableHiveSupport()
    return builder.getOrCreate()
