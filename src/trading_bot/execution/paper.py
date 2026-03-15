from __future__ import annotations

import random

from trading_bot.execution.base import ExecutionAdapter, ExecutionResult
from trading_bot.market_data.base import MarketSnapshot


class PaperExecutionAdapter(ExecutionAdapter):
    mode = "paper"

    def execute(
        self,
        snapshot: MarketSnapshot,
        side: str,
        order_notional: float,
    ) -> ExecutionResult:
        edge = abs(snapshot.signal_bps) / 10000 * order_notional
        friction = order_notional * 0.0006
        noise = random.uniform(-0.6, 0.6)
        realized_pnl = round(edge - friction + noise, 4)
        return ExecutionResult(
            mode=self.mode,
            side=side,
            symbol=snapshot.symbol,
            order_notional=order_notional,
            fill_price=snapshot.price,
            realized_pnl=realized_pnl,
            status="filled",
            metadata={"venue": snapshot.venue},
        )
