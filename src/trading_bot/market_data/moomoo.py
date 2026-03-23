from __future__ import annotations

import time
from datetime import datetime, timezone

import moomoo

from trading_bot.market_data.base import MarketDataAdapter, MarketSnapshot


class MoomooMarketDataAdapter(MarketDataAdapter):
    def __init__(
        self,
        symbol: str,
        host: str = "127.0.0.1",
        port: int = 11111,
        min_interval_sec: float = 1.0,
    ) -> None:
        self._symbol = symbol  # e.g. "US.AAPL"
        self._min_interval_sec = max(0.0, min_interval_sec)
        self._ctx = moomoo.OpenQuoteContext(host=host, port=port)
        self._last_request_monotonic: float | None = None

    def get_snapshot(self) -> MarketSnapshot:
        self._sleep_if_needed()
        ret_code, data = self._ctx.get_market_snapshot([self._symbol])
        self._last_request_monotonic = time.monotonic()
        if ret_code != moomoo.RET_OK:
            raise RuntimeError(f"Failed to fetch moomoo snapshot: {data}")
        try:
            row = data.iloc[0]
            return MarketSnapshot(
                symbol=str(row["code"]),
                price=float(row["last_price"]),
                signal_bps=0.0,
                ts=datetime.now(timezone.utc).isoformat(),
                venue="moomoo",
                source="market_snapshot",
                metadata={
                    "ask_price": str(row["ask_price"]),
                    "bid_price": str(row["bid_price"]),
                    "volume": str(row["volume"]),
                },
            )
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise RuntimeError("Invalid moomoo snapshot payload") from exc

    def close(self) -> None:
        self._ctx.close()

    def _sleep_if_needed(self) -> None:
        if self._last_request_monotonic is None or self._min_interval_sec <= 0:
            return
        elapsed = time.monotonic() - self._last_request_monotonic
        remaining = self._min_interval_sec - elapsed
        if remaining > 0:
            time.sleep(remaining)
