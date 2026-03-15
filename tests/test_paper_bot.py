import json
import tempfile
import unittest
from pathlib import Path

from trading_bot.bots.paper_cex_swing import run_paper_cex_swing


class PaperBotIntegrationTest(unittest.TestCase):
    def test_run_paper_bot_writes_report(self) -> None:
        config = {
            "bot": {
                "name": "integration-bot",
                "environment": "test",
                "data_dir": "data/runtime",
                "metrics_host": "127.0.0.1",
                "metrics_port": 0,
                "loop_interval_ms": 1,
                "max_iterations": 2,
            },
            "risk": {
                "max_position_notional": 1000.0,
                "max_daily_loss": 100.0,
                "max_consecutive_losses": 5,
                "min_order_interval_seconds": 0,
            },
            "strategy": {
                "symbol": "BTCJPY",
                "base_price": 10000000.0,
                "signal_threshold_bps": 0.0,
            },
            "market_data": {
                "adapter": "synthetic",
                "venue": {
                    "name": "synthetic-feed",
                    "kind": "research",
                    "symbol": "BTCJPY",
                },
            },
            "execution": {
                "mode": "paper",
                "adapter": "paper",
                "venue": {
                    "name": "paper-execution",
                    "kind": "paper",
                    "symbol": "BTCJPY",
                },
                "order_notional": 100.0,
            },
            "credentials": {},
        }
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_dir = Path(tmp_dir) / "project"
            config_dir = project_dir / "bots" / "cex_swing"
            config_dir.mkdir(parents=True)
            config_path = config_dir / "config.json"
            config_path.write_text(json.dumps(config), encoding="utf-8")

            run_paper_cex_swing(config_path)

            reports_file = (
                project_dir
                / "data"
                / "runtime"
                / "records"
                / "integration-bot"
                / "reports"
            )
            matches = list(reports_file.glob("*/events.ndjson"))
            self.assertEqual(len(matches), 1)
