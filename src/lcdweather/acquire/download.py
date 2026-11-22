"""Download the planned files concurrently and keep the manifest up to date."""

from __future__ import annotations

import hashlib
from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from lcdweather.acquire.fetch import CHUNK_BYTES, DownloadError, FetchOptions, fetch_to_file
from lcdweather.acquire.manifest import ManifestEntry, read_manifest, write_manifest
from lcdweather.acquire.targets import DownloadTarget

DEFAULT_WORKERS = 4


@dataclass
class DownloadSummary:
    downloaded: int = 0
    skipped: int = 0
    failures: list[str] = field(default_factory=list)


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(CHUNK_BYTES), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _is_already_downloaded(
    target: DownloadTarget, out_dir: Path, entry: ManifestEntry | None
) -> bool:
    """A file is kept when the manifest recorded this same URL at the size found on disk."""
    path = out_dir / target.relative_path
    return (
        entry is not None
        and entry.url == target.url
        and path.is_file()
        and path.stat().st_size == entry.bytes
    )


def download_one(
    target: DownloadTarget, out_dir: Path, options: FetchOptions, now: Callable[[], str]
) -> ManifestEntry:
    path = out_dir / target.relative_path
    fetch_to_file(target.url, path, options)
    return ManifestEntry(
        station=target.station_id,
        year=target.year,
        url=target.url,
        bytes=path.stat().st_size,
        sha256=sha256_of(path),
        downloaded_at=now(),
    )


def download_all(
    targets: Sequence[DownloadTarget],
    out_dir: Path,
    manifest_path: Path,
    options: FetchOptions,
    workers: int = DEFAULT_WORKERS,
    force: bool = False,
    now: Callable[[], str] = utc_now,
    report: Callable[[str], None] = print,
) -> DownloadSummary:
    """Fetch every target not already on disk; the manifest is rewritten after each file.

    Rerunning resumes: files recorded in the manifest and still present are skipped, and
    manifest rows of files outside ``targets`` are kept.
    """
    entries = read_manifest(manifest_path)
    summary = DownloadSummary()
    pending = []
    for target in targets:
        if not force and _is_already_downloaded(
            target, out_dir, entries.get((target.station_id, target.year))
        ):
            summary.skipped += 1
        else:
            pending.append(target)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {
            pool.submit(download_one, target, out_dir, options, now): target for target in pending
        }
        for future in as_completed(futures):
            target = futures[future]
            try:
                entry = future.result()
            except DownloadError as error:
                summary.failures.append(str(error))
                report(f"FAILED {target.relative_path}: {error}")
                continue
            entries[entry.key] = entry
            write_manifest(manifest_path, entries.values())
            summary.downloaded += 1
            report(f"ok {target.relative_path} {entry.bytes} bytes")
    return summary
