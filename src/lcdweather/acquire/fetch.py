"""Fetch one URL to a file, retrying and resuming a transfer that was cut short."""

from __future__ import annotations

import http.client
import os
import re
import shutil
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

USER_AGENT = "lcdweather-download/0.1 (python-urllib)"
CHUNK_BYTES = 1 << 20
PART_SUFFIX = ".part"
HTTP_PARTIAL_CONTENT = 206
HTTP_RANGE_NOT_SATISFIABLE = 416
RETRYABLE_HTTP_STATUS = frozenset({408, 425, 429, 500, 502, 503, 504})
CONTENT_RANGE = re.compile(r"bytes (\d+)-(\d+)/(\d+)")


class DownloadError(Exception):
    """The file could not be fetched."""


class _InterruptedTransfer(Exception):
    """The transfer ended early or could not be resumed; another attempt may succeed."""


@dataclass(frozen=True)
class FetchOptions:
    retries: int = 4
    timeout_seconds: float = 120.0
    backoff_seconds: float = 2.0


def _expected_size(response: http.client.HTTPResponse, offset: int) -> int | None:
    """Full size of the file according to the response, or None when it does not say."""
    if response.status == HTTP_PARTIAL_CONTENT:
        match = CONTENT_RANGE.fullmatch(response.headers.get("Content-Range", "").strip())
        if match is None or int(match.group(1)) != offset:
            raise _InterruptedTransfer("server answered the resume request with another range")
        return int(match.group(3))
    length = response.headers.get("Content-Length")
    return int(length) if length is not None else None


def _transfer(url: str, part: Path, timeout_seconds: float) -> None:
    """One attempt: append to ``part`` when the server honours the resume, else restart it."""
    offset = part.stat().st_size if part.exists() else 0
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    if offset:
        request.add_header("Range", f"bytes={offset}-")
    try:
        response = urllib.request.urlopen(request, timeout=timeout_seconds)
    except urllib.error.HTTPError as error:
        if error.code == HTTP_RANGE_NOT_SATISFIABLE and offset:
            error.close()
            part.unlink(missing_ok=True)
            raise _InterruptedTransfer("server rejected the resume offset") from error
        raise
    with response:
        resumed = response.status == HTTP_PARTIAL_CONTENT
        try:
            expected = _expected_size(response, offset)
        except _InterruptedTransfer:
            part.unlink(missing_ok=True)
            raise
        with part.open("ab" if resumed else "wb") as handle:
            shutil.copyfileobj(response, handle, CHUNK_BYTES)
    actual = part.stat().st_size
    if expected is not None and actual != expected:
        if actual > expected:
            part.unlink(missing_ok=True)
        raise _InterruptedTransfer(f"got {actual} of {expected} bytes")


def fetch_to_file(
    url: str,
    destination: Path,
    options: FetchOptions,
    sleep: Callable[[float], None] = time.sleep,
) -> None:
    """Download ``url`` to ``destination``; the file appears only once it is complete."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    part = destination.with_name(destination.name + PART_SUFFIX)
    # A part file left by an earlier run may belong to an older version of the remote file.
    part.unlink(missing_ok=True)
    attempts = options.retries + 1
    last_error: Exception | None = None
    for attempt in range(attempts):
        if attempt:
            sleep(options.backoff_seconds * 2 ** (attempt - 1))
        try:
            _transfer(url, part, options.timeout_seconds)
        except urllib.error.HTTPError as error:
            error.close()
            if error.code not in RETRYABLE_HTTP_STATUS:
                part.unlink(missing_ok=True)
                raise DownloadError(f"{url}: HTTP {error.code} {error.reason}") from error
            last_error = error
        except (_InterruptedTransfer, http.client.HTTPException, OSError) as error:
            last_error = error
        else:
            os.replace(part, destination)
            return
    raise DownloadError(f"{url}: gave up after {attempts} attempts: {last_error}") from last_error
