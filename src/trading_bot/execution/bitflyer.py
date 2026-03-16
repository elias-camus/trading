from __future__ import annotations

import hashlib
import hmac
import json
import time

import requests

from trading_bot.execution.base import ExecutionAdapter, ExecutionResult
from trading_bot.market_data.base import MarketSnapshot


class BitFlyerExecutionAdapter(ExecutionAdapter):
    _ORDER_PATH = "/v1/me/sendchildorder"
    _ORDER_URL = f"https://api.bitflyer.com{_ORDER_PATH}"

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        mode: str,
        session: requests.Session | None = None,
    ) -> None:
        if mode not in {"dry-run", "live"}:
            raise ValueError(f"Unsupported BitFlyer execution mode: {mode}")
        self.mode = mode
        self._api_key = api_key
        self._api_secret = api_secret
        self._session = session or requests.Session()

    def execute(
        self,
        snapshot: MarketSnapshot,
        side: str,
        order_notional: float,
    ) -> ExecutionResult:
        if snapshot.price <= 0:
            raise RuntimeError("Snapshot price must be positive")

        size = round(order_notional / snapshot.price, 8)
        payload = {
            "product_code": snapshot.symbol,
            "child_order_type": "MARKET",
            "side": side,
            "size": size,
        }
        body = json.dumps(payload, separators=(",", ":"))
        headers = self._build_auth_headers("POST", self._ORDER_PATH, body)
        headers["Content-Type"] = "application/json"

        metadata = {
            "venue": snapshot.venue,
            "access_timestamp": headers["ACCESS-TIMESTAMP"],
        }

        if self.mode == "dry-run":
            return ExecutionResult(
                mode=self.mode,
                side=side,
                symbol=snapshot.symbol,
                order_notional=order_notional,
                fill_price=0.0,
                realized_pnl=0.0,
                status="dry-run",
                metadata=metadata,
            )

        try:
            response = self._session.post(
                self._ORDER_URL,
                data=body,
                headers=headers,
                timeout=10,
            )
            response.raise_for_status()
            response_payload = response.json()
        except (requests.RequestException, ValueError) as exc:
            raise RuntimeError("Failed to send BitFlyer child order") from exc

        acceptance_id = response_payload.get("child_order_acceptance_id")
        if not acceptance_id:
            raise RuntimeError("Invalid BitFlyer child order response")
        metadata["child_order_acceptance_id"] = str(acceptance_id)

        return ExecutionResult(
            mode=self.mode,
            side=side,
            symbol=snapshot.symbol,
            order_notional=order_notional,
            fill_price=0.0,
            realized_pnl=0.0,
            status="submitted",
            metadata=metadata,
        )

    def close(self) -> None:
        self._session.close()

    def _build_auth_headers(
        self,
        method: str,
        path: str,
        body: str,
    ) -> dict[str, str]:
        timestamp = str(int(time.time()))
        text = f"{timestamp}{method}{path}{body}"
        sign = hmac.new(
            self._api_secret.encode("utf-8"),
            text.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return {
            "ACCESS-KEY": self._api_key,
            "ACCESS-TIMESTAMP": timestamp,
            "ACCESS-SIGN": sign,
        }
