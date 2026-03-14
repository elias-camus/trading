from __future__ import annotations

import json
import threading
from collections import defaultdict
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import DefaultDict


@dataclass
class MetricSample:
    name: str
    value: float


class MetricsRegistry:
    def __init__(self) -> None:
        self._gauges: dict[str, float] = {}
        self._counters: DefaultDict[str, float] = defaultdict(float)
        self._lock = threading.Lock()

    def set_gauge(self, name: str, value: float) -> None:
        with self._lock:
            self._gauges[name] = value

    def inc_counter(self, name: str, value: float = 1.0) -> None:
        with self._lock:
            self._counters[name] += value

    def snapshot(self) -> dict[str, dict[str, float]]:
        with self._lock:
            return {
                "gauges": dict(self._gauges),
                "counters": dict(self._counters),
            }

    def render_prometheus(self) -> str:
        parts: list[str] = []
        snap = self.snapshot()
        for name, value in sorted(snap["gauges"].items()):
            parts.append(f"# TYPE {name} gauge")
            parts.append(f"{name} {value}")
        for name, value in sorted(snap["counters"].items()):
            parts.append(f"# TYPE {name} counter")
            parts.append(f"{name} {value}")
        return "\n".join(parts) + "\n"


class MetricsServer:
    def __init__(self, host: str, port: int, registry: MetricsRegistry) -> None:
        self._host = host
        self._port = port
        self._registry = registry
        self._server: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None
        self._start_error: str | None = None

    @property
    def start_error(self) -> str | None:
        return self._start_error

    def start(self) -> bool:
        registry = self._registry

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:  # noqa: N802
                if self.path == "/metrics":
                    payload = registry.render_prometheus().encode()
                    self.send_response(200)
                    self.send_header("Content-Type", "text/plain; version=0.0.4")
                    self.send_header("Content-Length", str(len(payload)))
                    self.end_headers()
                    self.wfile.write(payload)
                    return

                if self.path == "/healthz":
                    payload = json.dumps({"ok": True}).encode()
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(payload)))
                    self.end_headers()
                    self.wfile.write(payload)
                    return

                self.send_response(404)
                self.end_headers()

            def log_message(self, format: str, *args: object) -> None:
                return

        try:
            self._server = ThreadingHTTPServer((self._host, self._port), Handler)
        except OSError as exc:
            self._start_error = str(exc)
            self._server = None
            return False

        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        self._start_error = None
        return True

    def stop(self) -> None:
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
        if self._thread is not None:
            self._thread.join(timeout=2)
