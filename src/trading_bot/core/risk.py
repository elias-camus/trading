from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from trading_bot.core.config import RiskConfig


@dataclass
class RiskState:
    current_position_notional: float = 0.0
    daily_realized_pnl: float = 0.0
    consecutive_losses: int = 0
    last_order_at: datetime | None = None


class RiskManager:
    def __init__(self, config: RiskConfig) -> None:
        self._config = config
        self._state = RiskState()

    @property
    def state(self) -> RiskState:
        return self._state

    def can_open_order(self, order_notional: float) -> tuple[bool, str]:
        now = datetime.now(timezone.utc)

        if self._state.daily_realized_pnl <= -self._config.max_daily_loss:
            return False, "daily_loss_limit"
        if self._state.consecutive_losses >= self._config.max_consecutive_losses:
            return False, "consecutive_loss_limit"
        if (
            self._state.last_order_at is not None
            and now - self._state.last_order_at
            < timedelta(seconds=self._config.min_order_interval_seconds)
        ):
            return False, "min_order_interval"
        if (
            self._state.current_position_notional + order_notional
            > self._config.max_position_notional
        ):
            return False, "position_limit"
        return True, "ok"

    def register_fill(self, order_notional: float, realized_pnl: float) -> None:
        self._state.current_position_notional = max(
            0.0,
            self._state.current_position_notional + order_notional,
        )
        self._state.daily_realized_pnl += realized_pnl
        self._state.last_order_at = datetime.now(timezone.utc)
        if realized_pnl < 0:
            self._state.consecutive_losses += 1
        else:
            self._state.consecutive_losses = 0

    def flatten_position(self) -> None:
        self._state.current_position_notional = 0.0
