from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class MarketSnapshot:
    symbol: str
    price: float
    signal_bps: float
    ts: str
    venue: str
    source: str
    metadata: dict[str, str] = field(default_factory=dict)

    def to_record(self) -> dict[str, object]:
        return {
            "symbol": self.symbol,
            "price": self.price,
            "signal_bps": self.signal_bps,
            "ts": self.ts,
            "venue": self.venue,
            "source": self.source,
            "metadata": self.metadata,
        }


class MarketDataAdapter(ABC):
    @abstractmethod
    def get_snapshot(self) -> MarketSnapshot:
        raise NotImplementedError

    def close(self) -> None:
        return
