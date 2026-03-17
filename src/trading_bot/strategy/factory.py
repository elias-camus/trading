from __future__ import annotations

from trading_bot.core.config import SwingStrategyConfig
from trading_bot.strategy.base import Strategy
from trading_bot.strategy.momentum import MomentumStrategy
from trading_bot.strategy.passthrough import PassthroughStrategy


def build_strategy(config: SwingStrategyConfig) -> Strategy:
    strategy_type = config.metadata.get("strategy_type", "passthrough")
    if strategy_type == "passthrough":
        return PassthroughStrategy()
    if strategy_type == "momentum":
        lookback = int(config.metadata.get("momentum_lookback", "10"))
        return MomentumStrategy(lookback=lookback)
    raise ValueError(f"Unsupported strategy type: {strategy_type}")
