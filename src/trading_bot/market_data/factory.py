from __future__ import annotations

from trading_bot.core.config import AppConfig
from trading_bot.market_data.base import MarketDataAdapter
from trading_bot.market_data.synthetic import SyntheticMarketDataAdapter


def build_market_data_adapter(config: AppConfig) -> MarketDataAdapter:
    adapter = config.market_data.adapter
    if adapter == "synthetic":
        return SyntheticMarketDataAdapter(config)
    raise ValueError(f"Unsupported market data adapter: {adapter}")
