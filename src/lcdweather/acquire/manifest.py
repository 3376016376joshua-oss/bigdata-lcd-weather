"""The download manifest: one row per downloaded station-year file."""

from __future__ import annotations

import csv
import os
from collections.abc import Iterable
from dataclasses import asdict, dataclass, fields
from pathlib import Path


@dataclass(frozen=True)
class ManifestEntry:
    station: str
    year: int
    url: str
    bytes: int
    sha256: str
    downloaded_at: str

    @property
    def key(self) -> tuple[str, int]:
        return (self.station, self.year)


MANIFEST_COLUMNS = tuple(field.name for field in fields(ManifestEntry))


def read_manifest(path: Path) -> dict[tuple[str, int], ManifestEntry]:
    """Entries by (station, year); empty when the manifest does not exist yet."""
    if not path.is_file():
        return {}
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if tuple(reader.fieldnames or ()) != MANIFEST_COLUMNS:
            raise ValueError(f"{path}: expected columns {','.join(MANIFEST_COLUMNS)}")
        entries = [
            ManifestEntry(
                station=row["station"],
                year=int(row["year"]),
                url=row["url"],
                bytes=int(row["bytes"]),
                sha256=row["sha256"],
                downloaded_at=row["downloaded_at"],
            )
            for row in reader
        ]
    return {entry.key: entry for entry in entries}


def write_manifest(path: Path, entries: Iterable[ManifestEntry]) -> None:
    """Write the entries sorted by station and year, replacing the file in one step."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=MANIFEST_COLUMNS, lineterminator="\n")
        writer.writeheader()
        for entry in sorted(entries, key=lambda entry: entry.key):
            writer.writerow(asdict(entry))
    os.replace(temporary, path)
