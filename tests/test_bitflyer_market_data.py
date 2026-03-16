import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import requests

from trading_bot.core.config import AppConfig
from trading_bot.market_data.bitflyer import BitFlyerMarketDataAdapter
from trading_bot.market_data.factory import build_market_data_adapter


class BitFlyerMarketDataAdapterTest(unittest.TestCase):
    def test_builds_snapshot_from_ticker_payload(self) -> None:
        session = Mock()
        response = Mock()
        response.json.return_value = {
            "product_code": "BTC_JPY",
            "ltp": 12345678,
            "timestamp": "2026-03-16T00:00:00.123",
            "best_bid": 12345000,
            "best_ask": 12346000,
            "volume_by_product": 12.34,
        }
        response.raise_for_status.return_value = None
        session.get.return_value = response

        adapter = BitFlyerMarketDataAdapter(session=session, min_interval_sec=0.0)

        snapshot = adapter.get_snapshot()

        self.assertEqual(snapshot.symbol, "BTC_JPY")
        self.assertEqual(snapshot.price, 12345678.0)
        self.assertEqual(snapshot.signal_bps, 0.0)
        self.assertEqual(snapshot.ts, "2026-03-16T00:00:00.123")
        self.assertEqual(snapshot.venue, "bitflyer")
        self.assertEqual(snapshot.source, "http_ticker")
        self.assertEqual(snapshot.metadata["best_bid"], "12345000")
        self.assertEqual(snapshot.metadata["best_ask"], "12346000")
        self.assertEqual(snapshot.metadata["volume_by_product"], "12.34")

    def test_raises_runtime_error_on_http_failure(self) -> None:
        session = Mock()
        session.get.side_effect = requests.RequestException("boom")
        adapter = BitFlyerMarketDataAdapter(session=session, min_interval_sec=0.0)

        with self.assertRaises(RuntimeError):
            adapter.get_snapshot()

    def test_enforces_minimum_interval_between_requests(self) -> None:
        session = Mock()
        response = Mock()
        response.json.return_value = {
            "product_code": "BTC_JPY",
            "ltp": 1,
            "timestamp": "2026-03-16T00:00:00Z",
            "best_bid": 1,
            "best_ask": 2,
            "volume_by_product": 3,
        }
        response.raise_for_status.return_value = None
        session.get.return_value = response
        adapter = BitFlyerMarketDataAdapter(session=session, min_interval_sec=1.0)

        with patch("trading_bot.market_data.bitflyer.time.monotonic", side_effect=[100.0, 100.3, 100.3]):
            with patch("trading_bot.market_data.bitflyer.time.sleep") as sleep_mock:
                adapter.get_snapshot()
                adapter.get_snapshot()

        sleep_mock.assert_called_once()
        self.assertAlmostEqual(sleep_mock.call_args.args[0], 0.7)


class BitFlyerMarketDataFactoryTest(unittest.TestCase):
    def test_build_market_data_adapter_supports_source_alias(self) -> None:
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
                "source": "bitflyer",
                "venue": {
                    "name": "bitflyer",
                    "kind": "cex",
                    "symbol": "BTC_JPY",
                },
                "product_code": "FX_BTC_JPY",
                "min_interval_sec": 2.5,
            },
            "execution": {
                "mode": "paper",
                "adapter": "paper",
                "venue": {
                    "name": "paper",
                    "kind": "paper",
                    "symbol": "BTC_JPY",
                },
                "order_notional": 250,
            },
            "credentials": {},
        }
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_path = Path(tmp_dir) / "config.json"
            config_path.write_text(json.dumps(payload), encoding="utf-8")
            config = AppConfig.load(config_path)

        adapter = build_market_data_adapter(config)

        self.assertIsInstance(adapter, BitFlyerMarketDataAdapter)
        self.assertEqual(adapter._product_code, "FX_BTC_JPY")
        self.assertEqual(adapter._min_interval_sec, 2.5)
