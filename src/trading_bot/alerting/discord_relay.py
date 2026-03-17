from __future__ import annotations

import json
import os
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib import request


@dataclass(frozen=True)
class DiscordDeliveryTarget:
    mode: str
    webhook_url: str | None = None
    bot_token: str | None = None
    channel_id: str | None = None


def _severity_prefix(status: str, severity: str) -> str:
    if status == "resolved":
        return "✅"
    if severity == "critical":
        return "🔴"
    if severity == "warning":
        return "🟡"
    return "ℹ️"


def _format_headline(status: str, alert_name: str, severity: str) -> str:
    prefix = _severity_prefix(status, severity)
    if status == "resolved":
        return f"{prefix} [{status}] {alert_name} severity={severity}"
    if severity == "critical":
        return f"{prefix} **[{status}] {alert_name} severity={severity}**"
    return f"{prefix} [{status}] {alert_name} severity={severity}"


def _resolve_webhook_url_from_secret(secret_name: str) -> str:
    try:
        import boto3
    except ImportError as exc:
        raise RuntimeError("boto3 is required for Discord webhook secrets") from exc

    region = os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION")
    session = boto3.session.Session(region_name=region)
    client = session.client("secretsmanager")
    response = client.get_secret_value(SecretId=secret_name)
    secret_string = response.get("SecretString")
    if secret_string is None:
        raise ValueError("Discord webhook secret payload was empty")

    try:
        payload = json.loads(secret_string)
    except json.JSONDecodeError:
        return secret_string

    webhook_value = payload.get("webhook_url")
    if not webhook_value:
        raise ValueError("Discord webhook secret must include webhook_url")
    return str(webhook_value)


def resolve_webhook_url() -> str | None:
    target = resolve_discord_delivery_target()
    return target.webhook_url


def resolve_discord_delivery_target() -> DiscordDeliveryTarget:
    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")
    if webhook_url:
        return DiscordDeliveryTarget(mode="webhook", webhook_url=webhook_url)

    secret_name = os.environ.get("DISCORD_WEBHOOK_SECRET_NAME")
    if secret_name:
        webhook_url = _resolve_webhook_url_from_secret(secret_name)
        return DiscordDeliveryTarget(mode="webhook", webhook_url=webhook_url)

    bot_token = os.environ.get("DISCORD_BOT_TOKEN")
    channel_id = os.environ.get("DISCORD_CHANNEL_ID")
    if bot_token and channel_id:
        return DiscordDeliveryTarget(mode="bot", bot_token=bot_token, channel_id=channel_id)

    return DiscordDeliveryTarget(mode="none")


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
        bot_name = labels.get("bot_name")
        venue = labels.get("venue")
        summary = annotations.get("summary", "")
        description = annotations.get("description", "")
        lines.append(_format_headline(status, alert_name, severity))
        context_parts = []
        if bot_name:
            context_parts.append(f"bot={bot_name}")
        if venue:
            context_parts.append(f"venue={venue}")
        if context_parts:
            lines.append(" ".join(context_parts))
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


def send_discord_bot_message(bot_token: str, channel_id: str, message: str) -> None:
    payload = json.dumps({"content": message}).encode("utf-8")
    req = request.Request(
        f"https://discord.com/api/v10/channels/{channel_id}/messages",
        data=payload,
        headers={
            "Authorization": f"Bot {bot_token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=10) as response:
            status = getattr(response, "status", None)
            if status is not None and status >= 400:
                raise RuntimeError(f"Discord bot API returned status={status}")
    except RuntimeError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"failed to send Discord bot message: {exc}") from exc


def serve(host: str = "0.0.0.0", port: int = 9094) -> None:
    target = resolve_discord_delivery_target()

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:  # noqa: N802
            if self.path != "/alert":
                self.send_response(404)
                self.end_headers()
                return

            body = self.rfile.read(int(self.headers.get("Content-Length", "0")))
            payload = json.loads(body or b"{}")
            message = build_message(payload)
            if target.mode == "webhook" and target.webhook_url:
                try:
                    send_discord_message(target.webhook_url, message)
                except Exception as exc:  # noqa: BLE001
                    error = str(exc).encode("utf-8")
                    self.send_response(502)
                    self.send_header("Content-Type", "text/plain; charset=utf-8")
                    self.send_header("Content-Length", str(len(error)))
                    self.end_headers()
                    self.wfile.write(error)
                    return
            elif target.mode == "bot" and target.bot_token and target.channel_id:
                try:
                    send_discord_bot_message(target.bot_token, target.channel_id, message)
                except Exception as exc:  # noqa: BLE001
                    error = str(exc).encode("utf-8")
                    self.send_response(502)
                    self.send_header("Content-Type", "text/plain; charset=utf-8")
                    self.send_header("Content-Length", str(len(error)))
                    self.end_headers()
                    self.wfile.write(error)
                    return

            response = json.dumps({"ok": True, "delivered": target.mode != "none"}).encode("utf-8")
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
