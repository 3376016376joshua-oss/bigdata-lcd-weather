"""Write one small result table as a CSV, locally or on a cluster file system."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pyspark.sql import DataFrame

_LOCAL_SCHEME = "file://"


def is_cluster_path(results_dir: str) -> bool:
    """True for ``hdfs://``, ``gs://`` and other non-local URIs."""
    return "://" in results_dir and not results_dir.startswith(_LOCAL_SCHEME)


def write_cluster_csv(frame: DataFrame, target_dir: str) -> str:
    """Write ``frame`` as a directory holding a single CSV part file with a header."""
    frame.coalesce(1).write.mode("overwrite").option("header", "true").csv(target_dir)
    return target_dir


def write_local_csv(frame: DataFrame, target_file: Path) -> str:
    """Collect ``frame`` to the driver through Pandas and write one CSV file."""
    target_file.parent.mkdir(parents=True, exist_ok=True)
    frame.toPandas().to_csv(target_file, index=False)
    return str(target_file)


def write_result(frame: DataFrame, name: str, results_dir: str) -> str:
    """Write ``frame`` as the result ``name`` and return where it went.

    A local directory gets the file ``<name>.csv``. A cluster URI gets the directory
    ``<name>/``, ready for ``hdfs dfs -getmerge``.
    """
    if is_cluster_path(results_dir):
        return write_cluster_csv(frame, f"{results_dir.rstrip('/')}/{name}")
    return write_local_csv(frame, Path(results_dir.removeprefix(_LOCAL_SCHEME)) / f"{name}.csv")
