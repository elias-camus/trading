import json
import tempfile
import unittest
from pathlib import Path

from trading_bot.core.config import AppConfig


class AppConfigTest(unittest.TestCase):
    def test_loads_new_shape(self) -> None:
        payload = {
            "bot": {
                "name": "demo",
                "environment": "dev",
                "data_dir": "data/runtime",
                "metrics_host": "127.0.0.1",
                "metrics_port": 9100,
                "loop_interval_ms": 100,
                "max_iterations": 1,
            },
            "risk": {
                "max_position_notional": 1000,
                "max_daily_loss": 100,
                "max_consecutive_losses": 3,
                "min_order_interval_seconds": 1,
            },
            "strategy": {
                "symbol": "BTCJPY",
                "base_price": 100,
                "signal_threshold_bps": 5,
            },
            "market_data": {
                "adapter": "synthetic",
                "venue": {
                    "name": "bitbank",
                    "kind": "research",
                    "symbol": "BTCJPY",
                },
            },
            "execution": {
                "mode": "paper",
                "adapter": "paper",
                "venue": {
                    "name": "paper",
                    "kind": "paper",
                    "symbol": "BTCJPY",
                },
                "order_notional": 250,
            },
            "credentials": {
                "bitbank": {
                    "provider": "env",
                    "api_key_env": "BITBANK_API_KEY",
                    "api_secret_env": "BITBANK_API_SECRET",
                }
            },
        }
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_path = Path(tmp_dir) / "config.json"
            config_path.write_text(json.dumps(payload), encoding="utf-8")

            config = AppConfig.load(config_path)

        self.assertEqual(config.market_data.venue.name, "bitbank")
        self.assertEqual(config.execution.order_notional, 250.0)
        self.assertEqual(config.credentials["bitbank"].provider, "env")

    def test_loads_legacy_shape(self) -> None:
        payload = {
            "bot": {
                "name": "legacy",
                "environment": "dev",
                "data_dir": "data/runtime",
                "metrics_host": "127.0.0.1",
                "metrics_port": 9100,
                "loop_interval_ms": 100,
                "max_iterations": 1,
                "live_execution_enabled": False,
            },
            "risk": {
                "max_position_notional": 1000,
                "max_daily_loss": 100,
                "max_consecutive_losses": 3,
                "min_order_interval_seconds": 1,
            },
            "strategy": {
                "symbol": "BTCJPY",
                "base_price": 100,
                "signal_threshold_bps": 5,
                "order_notional": 250,
            },
        }
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_path = Path(tmp_dir) / "config.json"
            config_path.write_text(json.dumps(payload), encoding="utf-8")

            config = AppConfig.load(config_path)

        self.assertEqual(config.market_data.adapter, "synthetic")
        self.assertEqual(config.execution.adapter, "paper")
        self.assertEqual(config.execution.order_notional, 250.0)
