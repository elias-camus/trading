from __future__ import annotations

from collections import deque

from trading_bot.market_data.base import MarketSnapshot
from trading_bot.strategy.base import Strategy


class MomentumStrategy(Strategy):
    def __init__(self, lookback: int = 10) -> None:
        self._prices: deque[float] = deque(maxlen=max(2, lookback))

    def compute_signal_bps(self, snapshot: MarketSnapshot) -> float:
        self._prices.append(snapshot.price)
        if len(self._prices) < 2:
            return 0.0
        oldest = self._prices[0]
        if oldest <= 0:
            return 0.0
        return round((snapshot.price - oldest) / oldest * 10000, 2)
