from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

from trading_bot.bots.base import BaseBot


def run_paper_cex_swing(config_path: Path) -> None:
    PaperCexSwingBot(config_path).run()


class PaperCexSwingBot(BaseBot):
    def before_loop(self) -> None:
        self.wins = 0
        self.losses = 0

    def run_iteration(self, iteration: int) -> None:
        snapshot = self.market_data.get_snapshot()
        signal_bps = self.strategy.compute_signal_bps(snapshot)
        snapshot = replace(snapshot, signal_bps=signal_bps)
        self.recorder.record("market_snapshots", snapshot.to_record())
        self.registry.set_gauge("market_price", snapshot.price)
        self.registry.set_gauge("signal_bps", snapshot.signal_bps)
        self.registry.set_gauge("iterations_total", float(iteration + 1))

        if abs(snapshot.signal_bps) < self.config.strategy.signal_threshold_bps:
            self.recorder.record(
                "decisions",
                {
                    "iteration": iteration,
                    "action": "hold",
                    "reason": "signal_below_threshold",
                    "signal_bps": snapshot.signal_bps,
                    "venue": snapshot.venue,
                },
            )
            self.registry.inc_counter("bot_holds_total")
            return

        can_trade, reason = self.risk.can_open_order(self.config.execution.order_notional)
        if not can_trade:
            self.recorder.record(
                "risk_events",
                {
                    "iteration": iteration,
                    "blocked_reason": reason,
                    "signal_bps": snapshot.signal_bps,
                    "venue": snapshot.venue,
                },
            )
            self.registry.inc_counter("risk_blocks_total")
            return

        side = "buy" if snapshot.signal_bps > 0 else "sell"
        execution_result = self.execution.execute(
            snapshot,
            side,
            self.config.execution.order_notional,
        )
        self.risk.register_fill(
            self.config.execution.order_notional,
            execution_result.realized_pnl or 0.0,
        )
        if execution_result.realized_pnl is None:
            pass
        elif execution_result.realized_pnl >= 0:
            self.wins += 1
        else:
            self.losses += 1

        self.recorder.record(
            "paper_fills",
            {
                "iteration": iteration,
                **execution_result.to_record(),
                "signal_bps": snapshot.signal_bps,
            },
        )
        self.risk.flatten_position()
        self.registry.inc_counter("paper_trades_total")
        self.registry.set_gauge("daily_realized_pnl", self.risk.state.daily_realized_pnl)
        self.registry.set_gauge("consecutive_losses", self.risk.state.consecutive_losses)
        self.registry.set_gauge("wins_total", float(self.wins))
        self.registry.set_gauge("losses_total", float(self.losses))

    def after_loop(self) -> None:
        self.recorder.record(
            "reports",
            {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "wins": self.wins,
                "losses": self.losses,
                "daily_realized_pnl": self.risk.state.daily_realized_pnl,
                "consecutive_losses": self.risk.state.consecutive_losses,
                "execution_mode": self.config.execution.mode,
                "market_data_adapter": self.config.market_data.adapter,
            },
        )
