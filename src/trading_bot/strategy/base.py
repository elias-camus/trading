from __future__ import annotations

from abc import ABC, abstractmethod

from trading_bot.market_data.base import MarketSnapshot


class Strategy(ABC):
    @abstractmethod
    def compute_signal_bps(self, snapshot: MarketSnapshot) -> float:
        raise NotImplementedError
