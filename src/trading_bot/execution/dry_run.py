from __future__ import annotations

from trading_bot.execution.base import ExecutionAdapter, ExecutionResult
from trading_bot.market_data.base import MarketSnapshot


class DryRunExecutionAdapter(ExecutionAdapter):
    mode = "dry-run"

    def execute(
        self,
        snapshot: MarketSnapshot,
        side: str,
        order_notional: float,
    ) -> ExecutionResult:
        return ExecutionResult(
            mode=self.mode,
            side=side,
            symbol=snapshot.symbol,
            order_notional=order_notional,
            fill_price=snapshot.price,
            realized_pnl=0.0,
            status="simulated",
            metadata={"venue": snapshot.venue},
        )
