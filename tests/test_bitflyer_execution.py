import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import requests

from trading_bot.core.config import AppConfig
from trading_bot.execution.bitflyer import BitFlyerExecutionAdapter
from trading_bot.execution.factory import build_execution_adapter
from trading_bot.market_data.base import MarketSnapshot


class BitFlyerExecutionAdapterTest(unittest.TestCase):
    def test_dry_run_does_not_send_http_request(self) -> None:
        session = Mock()
        adapter = BitFlyerExecutionAdapter(
            api_key="key",
            api_secret="secret",
            mode="dry-run",
            session=session,
        )

        with patch("trading_bot.execution.bitflyer.time.time", return_value=1700000000):
            adapter.execute(self._snapshot(), "BUY", 250000.0)

        session.post.assert_not_called()

    def test_dry_run_returns_dry_run_status(self) -> None:
        adapter = BitFlyerExecutionAdapter(
            api_key="key",
            api_secret="secret",
            mode="dry-run",
            session=Mock(),
        )

        with patch("trading_bot.execution.bitflyer.time.time", return_value=1700000000):
            result = adapter.execute(self._snapshot(), "BUY", 250000.0)

        self.assertEqual(result.status, "dry-run")
        self.assertEqual(result.fill_price, 0.0)
        self.assertEqual(result.realized_pnl, 0.0)

    def test_live_mode_posts_expected_endpoint_and_body(self) -> None:
        session = Mock()
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "child_order_acceptance_id": "JRF20150707-000000-000000",
        }
        session.post.return_value = response
        adapter = BitFlyerExecutionAdapter(
            api_key="key",
            api_secret="secret",
            mode="live",
            session=session,
        )

        with patch("trading_bot.execution.bitflyer.time.time", return_value=1700000000):
            adapter.execute(self._snapshot(), "SELL", 250000.0)

        session.post.assert_called_once()
        self.assertEqual(
            session.post.call_args.args[0],
            "https://api.bitflyer.com/v1/me/sendchildorder",
        )
        self.assertEqual(
            json.loads(session.post.call_args.kwargs["data"]),
            {
                "product_code": "BTC_JPY",
                "child_order_type": "MARKET",
                "side": "SELL",
                "size": 0.005,
            },
        )

    def test_live_mode_includes_acceptance_id_in_metadata(self) -> None:
        session = Mock()
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "child_order_acceptance_id": "JRF20150707-111111-222222",
        }
        session.post.return_value = response
        adapter = BitFlyerExecutionAdapter(
            api_key="key",
            api_secret="secret",
            mode="live",
            session=session,
        )

        with patch("trading_bot.execution.bitflyer.time.time", return_value=1700000000):
            result = adapter.execute(self._snapshot(), "BUY", 250000.0)

        self.assertEqual(
            result.metadata["child_order_acceptance_id"],
            "JRF20150707-111111-222222",
        )
        self.assertEqual(result.status, "submitted")

    def test_raises_runtime_error_on_http_failure(self) -> None:
        session = Mock()
        session.post.side_effect = requests.RequestException("boom")
        adapter = BitFlyerExecutionAdapter(
            api_key="key",
            api_secret="secret",
            mode="live",
            session=session,
        )

        with patch("trading_bot.execution.bitflyer.time.time", return_value=1700000000):
            with self.assertRaises(RuntimeError):
                adapter.execute(self._snapshot(), "BUY", 250000.0)

    @staticmethod
    def _snapshot() -> MarketSnapshot:
        return MarketSnapshot(
            symbol="BTC_JPY",
            price=50000000.0,
            signal_bps=0.0,
            ts="2026-03-16T00:00:00Z",
            venue="bitflyer",
            source="http_ticker",
        )


class BitFlyerExecutionFactoryTest(unittest.TestCase):
    def test_build_execution_adapter_supports_bitflyer_dry_run(self) -> None:
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
                "symbol": "BTC_JPY",
                "base_price": 100,
                "signal_threshold_bps": 5,
            },
            "market_data": {
                "adapter": "synthetic",
                "venue": {
                    "name": "synthetic-feed",
                    "kind": "research",
                    "symbol": "BTC_JPY",
                },
            },
            "execution": {
                "mode": "dry-run",
                "adapter": "bitflyer-dry-run",
                "venue": {
                    "name": "bitflyer",
                    "kind": "cex",
                    "symbol": "BTC_JPY",
                },
                "order_notional": 250,
                "credentials_ref": "bitflyer",
            },
            "credentials": {
                "bitflyer": {
                    "provider": "inline",
                    "api_key": "key",
                    "api_secret": "secret",
                }
            },
        }
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_path = Path(tmp_dir) / "config.json"
            config_path.write_text(json.dumps(payload), encoding="utf-8")
            config = AppConfig.load(config_path)

        adapter = build_execution_adapter(config)

        self.assertIsInstance(adapter, BitFlyerExecutionAdapter)
        self.assertEqual(adapter.mode, "dry-run")
