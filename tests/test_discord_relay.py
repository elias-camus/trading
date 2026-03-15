import unittest

from trading_bot.alerting.discord_relay import build_message


class DiscordRelayTest(unittest.TestCase):
    def test_build_message(self) -> None:
        payload = {
            "alerts": [
                {
                    "status": "firing",
                    "labels": {
                        "alertname": "TradingBotMetricsDown",
                        "severity": "critical",
                    },
                    "annotations": {
                        "summary": "metrics down",
                        "description": "bot metrics endpoint is unavailable",
                    },
                }
            ]
        }

        message = build_message(payload)

        self.assertIn("TradingBotMetricsDown", message)
        self.assertIn("metrics down", message)
