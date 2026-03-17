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
        # 0.06% 固定の簡易手数料。実際の BitFlyer 現物は 0.01〜0.15% (取引量ティアで変動)。
        # bid/ask スプレッドは未反映 (snapshot.metadata に best_bid/best_ask あり)。
        # noise は ±0.6円の一様乱数で、実際のスリッページ分布とは無関係。
        # 戦略の方向性を見るには十分だが、精密な損益評価には不向き。
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
