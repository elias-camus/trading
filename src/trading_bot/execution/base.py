from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from trading_bot.market_data.base import MarketSnapshot


@dataclass
class ExecutionResult:
    mode: str
    side: str
    symbol: str
    order_notional: float
    fill_price: float | None
    realized_pnl: float | None
    status: str
    metadata: dict[str, str] = field(default_factory=dict)

    def to_record(self) -> dict[str, object]:
        return {
            "mode": self.mode,
            "side": self.side,
            "symbol": self.symbol,
            "order_notional": self.order_notional,
            "fill_price": self.fill_price,
            "realized_pnl": self.realized_pnl,
            "status": self.status,
            "metadata": self.metadata,
        }


class ExecutionAdapter(ABC):
    @abstractmethod
    def execute(
        self,
        snapshot: MarketSnapshot,
        side: str,
        order_notional: float,
    ) -> ExecutionResult:
        raise NotImplementedError
