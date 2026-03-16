from __future__ import annotations

from trading_bot.core.config import AppConfig
from trading_bot.market_data.base import MarketDataAdapter
from trading_bot.market_data.bitflyer import BitFlyerMarketDataAdapter
from trading_bot.market_data.synthetic import SyntheticMarketDataAdapter


def build_market_data_adapter(config: AppConfig) -> MarketDataAdapter:
    adapter = config.market_data.adapter
    if adapter == "synthetic":
        return SyntheticMarketDataAdapter(config)
    if adapter == "bitflyer":
        return BitFlyerMarketDataAdapter(
            product_code=config.market_data.product_code,
            min_interval_sec=config.market_data.min_interval_sec,
        )
    raise ValueError(f"Unsupported market data adapter: {adapter}")
