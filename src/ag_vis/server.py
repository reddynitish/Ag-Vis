from __future__ import annotations

import json
import mimetypes
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from .model import VisualState, public_dict


STATIC_ROOT = Path(__file__).with_name("static")


class StateStore:
    def __init__(self) -> None:
        self._state = VisualState.initial()
        self._condition = threading.Condition()
        self._revision = 0

    def snapshot(self) -> tuple[int, VisualState]:
        with self._condition:
            return self._revision, self._state

    def publish(self, state: VisualState) -> None:
        with self._condition:
            self._state = state
            self._revision += 1
            self._condition.notify_all()

    def wait_after(self, revision: int, timeout: float = 15) -> tuple[int, VisualState]:
        with self._condition:
            self._condition.wait_for(lambda: self._revision > revision, timeout=timeout)
            return self._revision, self._state


def _json_bytes(value: object) -> bytes:
    return json.dumps(value, separators=(",", ":")).encode("utf-8")


def _handler(store: StateStore) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: object) -> None:
            return

        def _send(self, status: int, body: bytes, content_type: str) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:
            path = urlparse(self.path).path
            if path == "/health":
                self._send(200, b'{"ok":true}', "application/json")
                return
            if path == "/api/state":
                _, state = store.snapshot()
                self._send(200, _json_bytes(public_dict(state)), "application/json")
                return
            if path == "/api/events":
                self._events()
                return
            self._static(path)

        def _events(self) -> None:
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.end_headers()
            revision = -1
            try:
                while True:
                    next_revision, state = store.wait_after(revision)
                    if next_revision == revision:
                        self.wfile.write(b": keepalive\n\n")
                        self.wfile.flush()
                        continue
                    revision = next_revision
                    payload = _json_bytes(public_dict(state))
                    self.wfile.write(b"data: " + payload + b"\n\n")
                    self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                return

        def _static(self, path: str) -> None:
            name = "index.html" if path == "/" else path.lstrip("/")
            if name not in {"index.html", "styles.css", "app.js"}:
                self.send_error(404)
                return
            file_path = STATIC_ROOT / name
            if not file_path.exists():
                self.send_error(404)
                return
            content_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
            self._send(200, file_path.read_bytes(), content_type)

    return Handler


def create_server(host: str, port: int, store: StateStore) -> ThreadingHTTPServer:
    return ThreadingHTTPServer((host, port), _handler(store))
