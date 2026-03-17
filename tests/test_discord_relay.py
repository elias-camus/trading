import json
import os
import sys
import types
import unittest
from unittest.mock import Mock, patch

from trading_bot.alerting.discord_relay import (
    build_message,
    resolve_discord_delivery_target,
    resolve_webhook_url,
    send_discord_bot_message,
    send_discord_message,
)


class DiscordRelayMessageTest(unittest.TestCase):
    def test_build_message_formats_critical_with_context(self) -> None:
        payload = {
            "alerts": [
                {
                    "status": "firing",
                    "labels": {
                        "alertname": "TradingBotMetricsDown",
                        "severity": "critical",
                        "bot_name": "swing-bot",
                        "venue": "bitflyer",
                    },
                    "annotations": {
                        "summary": "metrics down",
                        "description": "bot metrics endpoint is unavailable",
                    },
                }
            ]
        }

        message = build_message(payload)

        self.assertIn("🔴", message)
        self.assertIn("**[firing] TradingBotMetricsDown severity=critical**", message)
        self.assertIn("bot=swing-bot", message)
        self.assertIn("venue=bitflyer", message)
        self.assertIn("metrics down", message)
        self.assertIn("bot metrics endpoint is unavailable", message)

    def test_build_message_formats_warning(self) -> None:
        payload = {
            "alerts": [
                {
                    "status": "firing",
                    "labels": {
                        "alertname": "RiskHigh",
                        "severity": "warning",
                    },
                }
            ]
        }

        message = build_message(payload)

        self.assertIn("🟡 [firing] RiskHigh severity=warning", message)

    def test_build_message_formats_resolved(self) -> None:
        payload = {
            "alerts": [
                {
                    "status": "resolved",
                    "labels": {
                        "alertname": "RiskRecovered",
                        "severity": "critical",
                    },
                }
            ]
        }

        message = build_message(payload)

        self.assertIn("✅ [resolved] RiskRecovered severity=critical", message)

    def test_build_message_formats_info_for_other_severity(self) -> None:
        payload = {
            "alerts": [
                {
                    "status": "firing",
                    "labels": {
                        "alertname": "BotInfo",
                        "severity": "info",
                    },
                }
            ]
        }

        message = build_message(payload)

        self.assertIn("ℹ️ [firing] BotInfo severity=info", message)


class DiscordRelayWebhookResolutionTest(unittest.TestCase):
    def test_resolve_webhook_url_prefers_env(self) -> None:
        with patch.dict(
            os.environ,
            {
                "DISCORD_WEBHOOK_URL": "https://discord.test/from-env",
                "DISCORD_WEBHOOK_SECRET_NAME": "trading/discord",
            },
            clear=False,
        ):
            resolved = resolve_webhook_url()

        self.assertEqual(resolved, "https://discord.test/from-env")

    def test_resolve_webhook_url_uses_secrets_manager(self) -> None:
        mock_client = Mock()
        mock_client.get_secret_value.return_value = {
            "SecretString": json.dumps({"webhook_url": "https://discord.test/from-secret"})
        }
        mock_session = Mock()
        mock_session.client.return_value = mock_client
        mock_boto3 = types.SimpleNamespace(
            session=types.SimpleNamespace(Session=Mock(return_value=mock_session))
        )

        with patch.dict(
            os.environ,
            {
                "DISCORD_WEBHOOK_SECRET_NAME": "trading/discord",
                "AWS_REGION": "ap-northeast-1",
            },
            clear=True,
        ):
            with patch.dict(sys.modules, {"boto3": mock_boto3}):
                resolved = resolve_webhook_url()

        self.assertEqual(resolved, "https://discord.test/from-secret")
        mock_boto3.session.Session.assert_called_once_with(region_name="ap-northeast-1")
        mock_session.client.assert_called_once_with("secretsmanager")
        mock_client.get_secret_value.assert_called_once_with(SecretId="trading/discord")

    def test_resolve_discord_delivery_target_prefers_webhook_env_over_bot(self) -> None:
        with patch.dict(
            os.environ,
            {
                "DISCORD_WEBHOOK_URL": "https://discord.test/from-env",
                "DISCORD_BOT_TOKEN": "bot-token",
                "DISCORD_CHANNEL_ID": "12345",
            },
            clear=True,
        ):
            target = resolve_discord_delivery_target()

        self.assertEqual(target.mode, "webhook")
        self.assertEqual(target.webhook_url, "https://discord.test/from-env")
        self.assertIsNone(target.bot_token)
        self.assertIsNone(target.channel_id)

    def test_resolve_discord_delivery_target_falls_back_to_bot(self) -> None:
        with patch.dict(
            os.environ,
            {
                "DISCORD_BOT_TOKEN": "bot-token",
                "DISCORD_CHANNEL_ID": "12345",
            },
            clear=True,
        ):
            target = resolve_discord_delivery_target()

        self.assertEqual(target.mode, "bot")
        self.assertEqual(target.bot_token, "bot-token")
        self.assertEqual(target.channel_id, "12345")
        self.assertIsNone(target.webhook_url)

    def test_resolve_discord_delivery_target_returns_none_when_unconfigured(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            target = resolve_discord_delivery_target()

        self.assertEqual(target.mode, "none")
        self.assertIsNone(target.webhook_url)
        self.assertIsNone(target.bot_token)
        self.assertIsNone(target.channel_id)


class DiscordRelayHttpTest(unittest.TestCase):
    def test_send_discord_message_posts_json_payload(self) -> None:
        response = Mock()
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)

        with patch("trading_bot.alerting.discord_relay.request.urlopen", return_value=response) as mock_urlopen:
            send_discord_message("https://discord.test/webhook", "hello")

        req = mock_urlopen.call_args.args[0]
        self.assertEqual(req.full_url, "https://discord.test/webhook")
        self.assertEqual(req.get_method(), "POST")
        self.assertEqual(req.headers["Content-type"], "application/json")
        self.assertEqual(json.loads(req.data.decode("utf-8")), {"content": "hello"})

    def test_send_discord_bot_message_posts_json_payload(self) -> None:
        response = Mock()
        response.status = 200
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)

        with patch("trading_bot.alerting.discord_relay.request.urlopen", return_value=response) as mock_urlopen:
            send_discord_bot_message("bot-token", "12345", "hello")

        req = mock_urlopen.call_args.args[0]
        self.assertEqual(req.full_url, "https://discord.com/api/v10/channels/12345/messages")
        self.assertEqual(req.get_method(), "POST")
        self.assertEqual(req.headers["Authorization"], "Bot bot-token")
        self.assertEqual(req.headers["Content-type"], "application/json")
        self.assertEqual(json.loads(req.data.decode("utf-8")), {"content": "hello"})
