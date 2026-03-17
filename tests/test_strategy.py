from __future__ import annotations

import unittest

from trading_bot.core.config import SwingStrategyConfig
from trading_bot.market_data.base import MarketSnapshot
from trading_bot.strategy.factory import build_strategy
from trading_bot.strategy.momentum import MomentumStrategy
from trading_bot.strategy.passthrough import PassthroughStrategy


def _snapshot(price: float = 100.0, signal_bps: float = 5.0) -> MarketSnapshot:
    return MarketSnapshot(
        symbol="BTCJPY",
        price=price,
        signal_bps=signal_bps,
        ts="2024-01-01T00:00:00Z",
        venue="test",
        source="test",
    )


class PassthroughStrategyTest(unittest.TestCase):
    def test_returns_snapshot_signal_bps(self) -> None:
        strategy = PassthroughStrategy()
        self.assertEqual(strategy.compute_signal_bps(_snapshot(signal_bps=12.3)), 12.3)

    def test_returns_zero_when_signal_is_zero(self) -> None:
        strategy = PassthroughStrategy()
        self.assertEqual(strategy.compute_signal_bps(_snapshot(signal_bps=0.0)), 0.0)


class MomentumStrategyTest(unittest.TestCase):
    def test_returns_zero_on_first_snapshot(self) -> None:
        strategy = MomentumStrategy(lookback=5)
        self.assertEqual(strategy.compute_signal_bps(_snapshot(price=100.0)), 0.0)

    def test_computes_positive_momentum(self) -> None:
        strategy = MomentumStrategy(lookback=3)
        strategy.compute_signal_bps(_snapshot(price=100.0))
        result = strategy.compute_signal_bps(_snapshot(price=101.0))
        self.assertAlmostEqual(result, 100.0)  # 1% = 100 bps

    def test_computes_negative_momentum(self) -> None:
        strategy = MomentumStrategy(lookback=3)
        strategy.compute_signal_bps(_snapshot(price=100.0))
        result = strategy.compute_signal_bps(_snapshot(price=99.0))
        self.assertAlmostEqual(result, -100.0)

    def test_lookback_window_caps_history(self) -> None:
        strategy = MomentumStrategy(lookback=3)
        strategy.compute_signal_bps(_snapshot(price=100.0))
        strategy.compute_signal_bps(_snapshot(price=200.0))
        strategy.compute_signal_bps(_snapshot(price=300.0))
        # oldest (100.0) is now evicted; oldest is 200.0
        result = strategy.compute_signal_bps(_snapshot(price=300.0))
        # (300 - 200) / 200 * 10000 = 5000 bps
        self.assertAlmostEqual(result, 5000.0)


class StrategyFactoryTest(unittest.TestCase):
    def test_builds_passthrough_by_default(self) -> None:
        config = SwingStrategyConfig(symbol="BTC", base_price=100.0, signal_threshold_bps=5.0)
        strategy = build_strategy(config)
        self.assertIsInstance(strategy, PassthroughStrategy)

    def test_builds_momentum_strategy(self) -> None:
        config = SwingStrategyConfig(
            symbol="BTC",
            base_price=100.0,
            signal_threshold_bps=5.0,
            metadata={"strategy_type": "momentum", "momentum_lookback": "5"},
        )
        strategy = build_strategy(config)
        self.assertIsInstance(strategy, MomentumStrategy)

    def test_raises_on_unknown_type(self) -> None:
        config = SwingStrategyConfig(
            symbol="BTC",
            base_price=100.0,
            signal_threshold_bps=5.0,
            metadata={"strategy_type": "unknown"},
        )
        with self.assertRaises(ValueError):
            build_strategy(config)
