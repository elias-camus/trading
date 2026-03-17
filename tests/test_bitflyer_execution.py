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

    def test_dry_run_normalizes_lowercase_side(self) -> None:
        adapter = BitFlyerExecutionAdapter(
            api_key="key",
            api_secret="secret",
            mode="dry-run",
            session=Mock(),
        )

        with patch("trading_bot.execution.bitflyer.time.time", return_value=1700000000):
            result = adapter.execute(self._snapshot(), "buy", 250000.0)

        self.assertEqual(result.side, "BUY")

    def test_live_mode_posts_expected_endpoint_and_body(self) -> None:
        session = Mock()
        order_response = Mock()
        order_response.raise_for_status.return_value = None
        order_response.json.return_value = {
            "child_order_acceptance_id": "JRF20150707-000000-000000",
        }
        executions_response = Mock()
        executions_response.raise_for_status.return_value = None
        executions_response.json.return_value = [{"price": 50000000, "size": 0.005}]
        session.post.return_value = order_response
        session.get.return_value = executions_response
        adapter = BitFlyerExecutionAdapter(
            api_key="key",
            api_secret="secret",
            mode="live",
            session=session,
        )

        with patch("trading_bot.execution.bitflyer.time.time", return_value=1700000000):
            with patch("trading_bot.execution.bitflyer.time.monotonic", side_effect=[100.0, 100.1]):
                with patch("trading_bot.execution.bitflyer.time.sleep"):
                    adapter.execute(self._snapshot(), "sell", 250000.0)

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

    def test_raises_runtime_error_for_invalid_side(self) -> None:
        adapter = BitFlyerExecutionAdapter(
            api_key="key",
            api_secret="secret",
            mode="dry-run",
            session=Mock(),
        )

        with self.assertRaises(RuntimeError):
            adapter.execute(self._snapshot(), "hold", 250000.0)

    def test_live_mode_includes_acceptance_id_in_metadata(self) -> None:
        session = Mock()
        order_response = Mock()
        order_response.raise_for_status.return_value = None
        order_response.json.return_value = {
            "child_order_acceptance_id": "JRF20150707-111111-222222",
        }
        executions_response = Mock()
        executions_response.raise_for_status.return_value = None
        executions_response.json.return_value = [
            {"price": 50001000, "size": 0.002},
            {"price": 50002000, "size": 0.003},
        ]
        session.post.return_value = order_response
        session.get.return_value = executions_response
        adapter = BitFlyerExecutionAdapter(
            api_key="key",
            api_secret="secret",
            mode="live",
            session=session,
        )

        with patch("trading_bot.execution.bitflyer.time.time", return_value=1700000000):
            with patch("trading_bot.execution.bitflyer.time.monotonic", side_effect=[100.0, 100.1]):
                with patch("trading_bot.execution.bitflyer.time.sleep"):
                    result = adapter.execute(self._snapshot(), "BUY", 250000.0)

        self.assertEqual(
            result.metadata["child_order_acceptance_id"],
            "JRF20150707-111111-222222",
        )
        self.assertEqual(result.status, "submitted")
        self.assertEqual(result.fill_price, 50001600.0)
        self.assertIsNone(result.realized_pnl)
        self.assertEqual(result.metadata["executed_size"], "0.00500000")

    def test_live_mode_returns_none_fill_price_when_execution_is_not_ready(self) -> None:
        session = Mock()
        order_response = Mock()
        order_response.raise_for_status.return_value = None
        order_response.json.return_value = {
            "child_order_acceptance_id": "JRF20150707-111111-222222",
        }
        executions_response = Mock()
        executions_response.raise_for_status.return_value = None
        executions_response.json.return_value = []
        session.post.return_value = order_response
        session.get.return_value = executions_response
        adapter = BitFlyerExecutionAdapter(
            api_key="key",
            api_secret="secret",
            mode="live",
            session=session,
        )

        with patch("trading_bot.execution.bitflyer.time.time", return_value=1700000000):
            with patch(
                "trading_bot.execution.bitflyer.time.monotonic",
                side_effect=[100.0, 100.5, 101.0, 101.5, 102.0, 102.5, 103.1],
            ):
                with patch("trading_bot.execution.bitflyer.time.sleep"):
                    result = adapter.execute(self._snapshot(), "BUY", 250000.0)

        self.assertIsNone(result.fill_price)
        self.assertIsNone(result.realized_pnl)

    def test_live_mode_requests_executions_by_acceptance_id(self) -> None:
        session = Mock()
        order_response = Mock()
        order_response.raise_for_status.return_value = None
        order_response.json.return_value = {
            "child_order_acceptance_id": "JRF20150707-111111-222222",
        }
        executions_response = Mock()
        executions_response.raise_for_status.return_value = None
        executions_response.json.return_value = [{"price": 50000000, "size": 0.005}]
        session.post.return_value = order_response
        session.get.return_value = executions_response
        adapter = BitFlyerExecutionAdapter(
            api_key="key",
            api_secret="secret",
            mode="live",
            session=session,
        )

        with patch("trading_bot.execution.bitflyer.time.time", return_value=1700000000):
            with patch("trading_bot.execution.bitflyer.time.monotonic", side_effect=[100.0, 100.1]):
                with patch("trading_bot.execution.bitflyer.time.sleep"):
                    adapter.execute(self._snapshot(), "BUY", 250000.0)

        self.assertEqual(
            session.get.call_args.kwargs["params"],
            {
                "product_code": "BTC_JPY",
                "child_order_acceptance_id": "JRF20150707-111111-222222",
            },
        )

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

    def test_raises_runtime_error_when_fetching_executions_fails(self) -> None:
        session = Mock()
        order_response = Mock()
        order_response.raise_for_status.return_value = None
        order_response.json.return_value = {
            "child_order_acceptance_id": "JRF20150707-111111-222222",
        }
        session.post.return_value = order_response
        session.get.side_effect = requests.RequestException("boom")
        adapter = BitFlyerExecutionAdapter(
            api_key="key",
            api_secret="secret",
            mode="live",
            session=session,
        )

        with patch("trading_bot.execution.bitflyer.time.time", return_value=1700000000):
            with patch("trading_bot.execution.bitflyer.time.monotonic", side_effect=[100.0, 100.1]):
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
