#!/usr/bin/env python3
"""Download the NOAA LCD v2 station-year files and record them in the download manifest.

Standard library only. Run from the repository root:

    python3 scripts/download_lcd.py
    python3 scripts/download_lcd.py --years 2014-2015 --stations USW00094728 --out data/raw

Files land in ``<out>/<station_id>/LCD_<station_id>_<year>.csv``. Rerunning skips files that
are already recorded in the manifest and still on disk.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lcdweather.acquire.cli import add_selection_arguments, selected_targets  # noqa: E402
from lcdweather.acquire.download import DEFAULT_WORKERS, download_all  # noqa: E402
from lcdweather.acquire.fetch import FetchOptions  # noqa: E402
from lcdweather.config import load_settings  # noqa: E402

MANIFEST_NAME = "download_manifest.csv"


def parse_arguments(argv: list[str] | None) -> tuple[argparse.Namespace, list]:
    settings = load_settings()
    defaults = FetchOptions()
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    add_selection_arguments(parser, settings)
    parser.add_argument("--out", type=Path, default=Path(settings.local_raw_dir))
    parser.add_argument(
        "--manifest", type=Path, default=Path(settings.manifests_dir) / MANIFEST_NAME
    )
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS)
    parser.add_argument("--retries", type=int, default=defaults.retries)
    parser.add_argument("--timeout", type=float, default=defaults.timeout_seconds)
    parser.add_argument("--force", action="store_true", help="download again files already present")
    arguments = parser.parse_args(argv)
    if arguments.workers < 1 or arguments.retries < 0:
        parser.error("--workers must be at least 1 and --retries at least 0")
    try:
        targets = selected_targets(arguments, settings)
    except (OSError, ValueError) as error:
        parser.error(str(error))
    return arguments, targets


def main(argv: list[str] | None = None) -> int:
    arguments, targets = parse_arguments(argv)
    print(f"{len(targets)} files selected, saving under {arguments.out}")
    summary = download_all(
        targets,
        arguments.out,
        arguments.manifest,
        FetchOptions(retries=arguments.retries, timeout_seconds=arguments.timeout),
        workers=arguments.workers,
        force=arguments.force,
    )
    print(
        f"downloaded {summary.downloaded}, already present {summary.skipped}, "
        f"failed {len(summary.failures)}; manifest {arguments.manifest}"
    )
    return 1 if summary.failures else 0


if __name__ == "__main__":
    sys.exit(main())
