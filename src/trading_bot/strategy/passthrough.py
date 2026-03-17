from __future__ import annotations

from trading_bot.market_data.base import MarketSnapshot
from trading_bot.strategy.base import Strategy


class PassthroughStrategy(Strategy):
    def compute_signal_bps(self, snapshot: MarketSnapshot) -> float:
        return snapshot.signal_bps
