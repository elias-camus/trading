from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib import request


def build_message(payload: dict[str, Any]) -> str:
    alerts = payload.get("alerts", [])
    if not alerts:
        return "Alertmanager relay received an empty alert payload."

    lines = []
    for alert in alerts:
        status = alert.get("status", "unknown")
        labels = alert.get("labels", {})
        annotations = alert.get("annotations", {})
        alert_name = labels.get("alertname", "unknown")
        severity = labels.get("severity", "unknown")
        summary = annotations.get("summary", "")
        description = annotations.get("description", "")
        lines.append(f"[{status}] {alert_name} severity={severity}")
        if summary:
            lines.append(summary)
        if description:
            lines.append(description)
    return "\n".join(lines)[:1900]


def send_discord_message(webhook_url: str, message: str) -> None:
    payload = json.dumps({"content": message}).encode("utf-8")
    req = request.Request(
        webhook_url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with request.urlopen(req, timeout=10):
        return


def serve(host: str = "0.0.0.0", port: int = 9094) -> None:
    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:  # noqa: N802
            if self.path != "/alert":
                self.send_response(404)
                self.end_headers()
                return

            body = self.rfile.read(int(self.headers.get("Content-Length", "0")))
            payload = json.loads(body or b"{}")
            message = build_message(payload)
            if webhook_url:
                try:
                    send_discord_message(webhook_url, message)
                except Exception as exc:  # noqa: BLE001
                    error = str(exc).encode("utf-8")
                    self.send_response(502)
                    self.send_header("Content-Type", "text/plain; charset=utf-8")
                    self.send_header("Content-Length", str(len(error)))
                    self.end_headers()
                    self.wfile.write(error)
                    return

            response = json.dumps({"ok": True, "delivered": bool(webhook_url)}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(response)))
            self.end_headers()
            self.wfile.write(response)

        def do_GET(self) -> None:  # noqa: N802
            if self.path != "/healthz":
                self.send_response(404)
                self.end_headers()
                return
            response = json.dumps({"ok": True}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(response)))
            self.end_headers()
            self.wfile.write(response)

        def log_message(self, format: str, *args: object) -> None:
            return

    server = ThreadingHTTPServer((host, port), Handler)
    try:
        server.serve_forever()
    finally:
        server.server_close()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "9094"))
    serve(port=port)
