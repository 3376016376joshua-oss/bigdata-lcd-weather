"""A local HTTP server that stands in for the NOAA file server in download tests."""

from __future__ import annotations

import re
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

RANGE_HEADER = re.compile(r"bytes=(\d+)-")


class FakeLcdServer:
    """Serves ``files`` (URL path to bytes) and can be told to fail in controlled ways.

    ``fail_first[path] = n`` answers the first n requests for a path with HTTP 503.
    ``cut_first[path] = n`` sends only n bytes of the first response, then drops the connection.
    ``honour_range = False`` makes the server ignore resume requests and resend the whole file.
    """

    def __init__(self, files: dict[str, bytes]):
        self.files = dict(files)
        self.fail_first: dict[str, int] = {}
        self.cut_first: dict[str, int] = {}
        self.honour_range = True
        self.requests: list[tuple[str, str | None]] = []
        self._lock = threading.Lock()
        self._server = ThreadingHTTPServer(("127.0.0.1", 0), self._handler_class())
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)

    @property
    def base_url(self) -> str:
        host, port = self._server.server_address[:2]
        return f"http://{host}:{port}"

    def requests_for(self, path: str) -> list[str | None]:
        """The Range header of each request made for ``path``, in order."""
        return [range_header for requested, range_header in self.requests if requested == path]

    def __enter__(self) -> FakeLcdServer:
        self._thread.start()
        return self

    def __exit__(self, *exc_info: object) -> None:
        self._server.shutdown()
        self._server.server_close()
        self._thread.join()

    def _take(self, counters: dict[str, int], path: str) -> int | None:
        """Pop the pending fault for ``path``; fail_first counts down, cut_first fires once."""
        with self._lock:
            if path not in counters:
                return None
            if counters is self.fail_first and counters[path] > 1:
                counters[path] -= 1
                return 1
            return counters.pop(path)

    def _handler_class(self) -> type[BaseHTTPRequestHandler]:
        server = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, format: str, *args: object) -> None:
                """Keep test output quiet."""

            def do_GET(self) -> None:
                range_header = self.headers.get("Range")
                with server._lock:
                    server.requests.append((self.path, range_header))
                body = server.files.get(self.path)
                if body is None:
                    self.send_error(404)
                    return
                if server._take(server.fail_first, self.path):
                    self.send_error(503)
                    return
                offset = 0
                match = RANGE_HEADER.fullmatch(range_header or "")
                if match and server.honour_range:
                    offset = int(match.group(1))
                    if offset >= len(body):
                        self.send_error(416)
                        return
                    self.send_response(206)
                    self.send_header("Content-Range", f"bytes {offset}-{len(body) - 1}/{len(body)}")
                else:
                    self.send_response(200)
                payload = body[offset:]
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                cut_at = server._take(server.cut_first, self.path)
                if cut_at is not None:
                    self.wfile.write(payload[:cut_at])
                    self.wfile.flush()
                    self.close_connection = True
                    return
                self.wfile.write(payload)

        return Handler
