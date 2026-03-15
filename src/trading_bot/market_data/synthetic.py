from __future__ import annotations

import random
from datetime import datetime, timezone

from trading_bot.core.config import AppConfig
from trading_bot.market_data.base import MarketDataAdapter, MarketSnapshot


class SyntheticMarketDataAdapter(MarketDataAdapter):
    def __init__(self, config: AppConfig) -> None:
        self._config = config

    def get_snapshot(self) -> MarketSnapshot:
        signal_bps = round(random.uniform(-20.0, 20.0), 2)
        price = round(
            self._config.strategy.base_price * (1 + signal_bps / 10000),
            2,
        )
        return MarketSnapshot(
            symbol=self._config.market_data.venue.symbol,
            price=price,
            signal_bps=signal_bps,
            ts=datetime.now(timezone.utc).isoformat(),
            venue=self._config.market_data.venue.name,
            source=self._config.market_data.adapter,
            metadata={
                "kind": self._config.market_data.venue.kind,
            },
        )
