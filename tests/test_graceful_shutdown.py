from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path


class GracefulShutdownTest(unittest.TestCase):
    def _write_config(self, tmp: Path) -> Path:
        config = {
            "bot": {
                "name": "shutdown-test",
                "environment": "test",
                "data_dir": str(tmp / "data"),
                "metrics_host": "127.0.0.1",
                "metrics_port": 0,
                "loop_interval_ms": 10,
                "max_iterations": 0,
            },
            "risk": {
                "max_position_notional": 1000.0,
                "max_daily_loss": 100.0,
                "max_consecutive_losses": 3,
                "min_order_interval_seconds": 0,
            },
            "strategy": {
                "symbol": "TEST",
                "base_price": 100.0,
                "signal_threshold_bps": 5.0,
            },
            "market_data": {
                "adapter": "synthetic",
                "venue": {"name": "test", "kind": "research", "symbol": "TEST"},
            },
            "execution": {
                "mode": "paper",
                "adapter": "paper",
                "venue": {"name": "test", "kind": "paper", "symbol": "TEST"},
                "order_notional": 100.0,
            },
            "credentials": {},
        }
        config_path = tmp / "bots" / "test" / "config.json"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(json.dumps(config))
        return config_path

    def test_stop_requested_stops_loop(self) -> None:
        from trading_bot.bots.paper_cex_swing import PaperCexSwingBot

        with tempfile.TemporaryDirectory() as tmp:
            config_path = self._write_config(Path(tmp))
            bot = PaperCexSwingBot(config_path)
            bot._stop_requested = True
            self.assertTrue(bot.should_stop(0))

    def test_should_stop_false_when_no_signal(self) -> None:
        from trading_bot.bots.paper_cex_swing import PaperCexSwingBot

        with tempfile.TemporaryDirectory() as tmp:
            config_path = self._write_config(Path(tmp))
            bot = PaperCexSwingBot(config_path)
            # max_iterations=0 and no stop signal → should not stop
            self.assertFalse(bot.should_stop(0))
            self.assertFalse(bot.should_stop(100))
