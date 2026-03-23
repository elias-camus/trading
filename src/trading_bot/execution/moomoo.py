from __future__ import annotations

import time

import moomoo

from trading_bot.execution.base import ExecutionAdapter, ExecutionResult
from trading_bot.market_data.base import MarketSnapshot


class MoomooExecutionAdapter(ExecutionAdapter):
    def __init__(
        self,
        trade_unlock_pwd: str,
        mode: str,
        host: str = "127.0.0.1",
        port: int = 11111,
        trd_env: str = moomoo.TrdEnv.REAL,
    ) -> None:
        if mode not in {"dry-run", "live"}:
            raise ValueError(f"Unsupported moomoo execution mode: {mode}")
        self.mode = mode
        self._trade_unlock_pwd = trade_unlock_pwd
        self._trd_env = trd_env
        self._ctx = moomoo.OpenSecTradeContext(
            filter_trdmarket=moomoo.TrdMarket.US,
            host=host,
            port=port,
            security_firm=moomoo.SecurityFirm.FUTUINC,
        )
        self._unlocked = False

    def execute(
        self,
        snapshot: MarketSnapshot,
        side: str,
        order_notional: float,
    ) -> ExecutionResult:
        if snapshot.price <= 0:
            raise RuntimeError("Snapshot price must be positive")
        normalized_side = side.upper()
        if normalized_side not in {"BUY", "SELL"}:
            raise RuntimeError("Moomoo side must be BUY or SELL")

        # US stocks trade in whole shares
        qty = max(1, int(order_notional / snapshot.price))
        trd_side = moomoo.TrdSide.BUY if normalized_side == "BUY" else moomoo.TrdSide.SELL
        metadata: dict[str, str] = {"venue": "moomoo", "qty": str(qty)}

        if self.mode == "dry-run":
            return ExecutionResult(
                mode=self.mode,
                side=normalized_side,
                symbol=snapshot.symbol,
                order_notional=order_notional,
                fill_price=0.0,
                realized_pnl=0.0,
                status="dry-run",
                metadata=metadata,
            )

        self._ensure_unlocked()
        ret_code, ret_data = self._ctx.place_order(
            price=0,
            qty=qty,
            code=snapshot.symbol,
            trd_side=trd_side,
            order_type=moomoo.OrderType.MARKET,
            trd_env=self._trd_env,
        )
        if ret_code != moomoo.RET_OK:
            raise RuntimeError(f"Failed to place moomoo order: {ret_data}")

        order_id = str(ret_data["order_id"].iloc[0])
        metadata["order_id"] = order_id

        fill_price = self._fetch_fill_price(order_id)
        metadata["fill_status"] = "confirmed" if fill_price is not None else "unconfirmed"

        return ExecutionResult(
            mode=self.mode,
            side=normalized_side,
            symbol=snapshot.symbol,
            order_notional=order_notional,
            fill_price=fill_price,
            realized_pnl=None,
            status="submitted",
            metadata=metadata,
        )

    def close(self) -> None:
        self._ctx.close()

    def _ensure_unlocked(self) -> None:
        if self._unlocked:
            return
        ret_code, ret_data = self._ctx.unlock_trade(password=self._trade_unlock_pwd)
        if ret_code != moomoo.RET_OK:
            raise RuntimeError(f"Failed to unlock moomoo trade: {ret_data}")
        self._unlocked = True

    def _fetch_fill_price(self, order_id: str) -> float | None:
        deadline = time.monotonic() + 5.0
        while time.monotonic() < deadline:
            ret_code, data = self._ctx.order_list_query(
                order_id=order_id,
                status_filter_list=[moomoo.OrderStatus.FILLED_ALL, moomoo.OrderStatus.FILLED_PART],
                trd_env=self._trd_env,
            )
            if ret_code == moomoo.RET_OK and len(data) > 0:
                try:
                    return round(float(data["dealt_avg_price"].iloc[0]), 4)
                except (KeyError, TypeError, ValueError):
                    return None
            time.sleep(0.5)
        return None
