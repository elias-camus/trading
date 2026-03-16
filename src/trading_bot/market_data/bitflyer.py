from __future__ import annotations

import time

import requests

from trading_bot.market_data.base import MarketDataAdapter, MarketSnapshot


class BitFlyerMarketDataAdapter(MarketDataAdapter):
    _TICKER_URL = "https://api.bitflyer.com/v1/getticker"

    def __init__(
        self,
        product_code: str = "BTC_JPY",
        min_interval_sec: float = 1.0,
        session: requests.Session | None = None,
    ) -> None:
        self._product_code = product_code
        self._min_interval_sec = max(0.0, min_interval_sec)
        self._session = session or requests.Session()
        self._last_request_monotonic: float | None = None

    def get_snapshot(self) -> MarketSnapshot:
        self._sleep_if_needed()
        try:
            response = self._session.get(
                self._TICKER_URL,
                params={"product_code": self._product_code},
                timeout=10,
            )
            response.raise_for_status()
            payload = response.json()
        except (requests.RequestException, ValueError) as exc:
            raise RuntimeError("Failed to fetch BitFlyer ticker") from exc
        self._last_request_monotonic = time.monotonic()

        try:
            return MarketSnapshot(
                symbol=str(payload["product_code"]),
                price=float(payload["ltp"]),
                signal_bps=0.0,
                ts=str(payload["timestamp"]),
                venue="bitflyer",
                source="http_ticker",
                metadata={
                    "best_bid": str(payload["best_bid"]),
                    "best_ask": str(payload["best_ask"]),
                    "volume_by_product": str(payload["volume_by_product"]),
                },
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise RuntimeError("Invalid BitFlyer ticker payload") from exc

    def close(self) -> None:
        self._session.close()

    def _sleep_if_needed(self) -> None:
        if self._last_request_monotonic is None or self._min_interval_sec <= 0:
            return
        elapsed = time.monotonic() - self._last_request_monotonic
        remaining = self._min_interval_sec - elapsed
        if remaining > 0:
            time.sleep(remaining)
