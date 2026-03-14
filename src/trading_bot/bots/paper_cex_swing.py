from __future__ import annotations

import random
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from trading_bot.core.config import AppConfig
from trading_bot.core.metrics import MetricsRegistry, MetricsServer
from trading_bot.core.recorder import EventRecorder
from trading_bot.core.risk import RiskManager
from trading_bot.core.runtime import RunLock, config_fingerprint


@dataclass
class MarketSnapshot:
    symbol: str
    price: float
    signal_bps: float
    ts: str


def run_paper_cex_swing(config_path: Path) -> None:
    config = AppConfig.load(config_path)
    data_dir = _resolve_data_dir(config_path, config.bot.data_dir)

    registry = MetricsRegistry()
    recorder = EventRecorder(root_dir=data_dir / "records", bot_name=config.bot.name)
    risk = RiskManager(config.risk)
    metrics_server = MetricsServer(
        config.bot.metrics_host,
        config.bot.metrics_port,
        registry,
    )

    lock_path = data_dir / "locks" / f"{config.bot.name}.lock"
    with RunLock(lock_path):
        metrics_available = metrics_server.start()
        try:
            _record_runtime_metadata(config, recorder, registry, metrics_available, metrics_server.start_error)
            _run_loop(config, recorder, registry, risk)
        finally:
            metrics_server.stop()


def _run_loop(
    config: AppConfig,
    recorder: EventRecorder,
    registry: MetricsRegistry,
    risk: RiskManager,
) -> None:
    wins = 0
    losses = 0
    iteration = 0

    while True:
        if config.bot.max_iterations > 0 and iteration >= config.bot.max_iterations:
            break
        started_at = time.perf_counter()
        snapshot = _generate_snapshot(config)
        recorder.record("market_snapshots", snapshot.__dict__)
        registry.set_gauge("market_price", snapshot.price)
        registry.set_gauge("signal_bps", snapshot.signal_bps)
        registry.set_gauge("iterations_total", float(iteration + 1))

        if abs(snapshot.signal_bps) < config.strategy.signal_threshold_bps:
            recorder.record(
                "decisions",
                {
                    "iteration": iteration,
                    "action": "hold",
                    "reason": "signal_below_threshold",
                    "signal_bps": snapshot.signal_bps,
                },
            )
            registry.inc_counter("bot_holds_total")
            _finish_iteration(started_at, registry, config)
            iteration += 1
            continue

        can_trade, reason = risk.can_open_order(config.strategy.order_notional)
        if not can_trade:
            recorder.record(
                "risk_events",
                {
                    "iteration": iteration,
                    "blocked_reason": reason,
                    "signal_bps": snapshot.signal_bps,
                },
            )
            registry.inc_counter("risk_blocks_total")
            _finish_iteration(started_at, registry, config)
            iteration += 1
            continue

        side = "buy" if snapshot.signal_bps > 0 else "sell"
        realized_pnl = _simulate_fill(snapshot.signal_bps, config.strategy.order_notional)
        risk.register_fill(config.strategy.order_notional, realized_pnl)
        if realized_pnl >= 0:
            wins += 1
        else:
            losses += 1

        recorder.record(
            "paper_fills",
            {
                "iteration": iteration,
                "side": side,
                "symbol": config.strategy.symbol,
                "price": snapshot.price,
                "signal_bps": snapshot.signal_bps,
                "order_notional": config.strategy.order_notional,
                "realized_pnl": realized_pnl,
                "live_execution_enabled": config.bot.live_execution_enabled,
            },
        )
        risk.flatten_position()
        registry.inc_counter("paper_trades_total")
        registry.set_gauge("daily_realized_pnl", risk.state.daily_realized_pnl)
        registry.set_gauge("consecutive_losses", risk.state.consecutive_losses)
        registry.set_gauge("wins_total", float(wins))
        registry.set_gauge("losses_total", float(losses))
        _finish_iteration(started_at, registry, config)
        iteration += 1

    if iteration == 0:
        recorder.record(
            "reports",
            {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "wins": wins,
                "losses": losses,
                "daily_realized_pnl": risk.state.daily_realized_pnl,
                "consecutive_losses": risk.state.consecutive_losses,
            },
        )
        return

    recorder.record(
        "reports",
        {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "wins": wins,
            "losses": losses,
            "daily_realized_pnl": risk.state.daily_realized_pnl,
            "consecutive_losses": risk.state.consecutive_losses,
        },
    )


def _record_runtime_metadata(
    config: AppConfig,
    recorder: EventRecorder,
    registry: MetricsRegistry,
    metrics_available: bool,
    metrics_start_error: str | None,
) -> None:
    recorder.record(
        "runtime",
        {
            "bot_name": config.bot.name,
            "environment": config.bot.environment,
            "config_fingerprint": config_fingerprint(config),
            "live_execution_enabled": config.bot.live_execution_enabled,
            "metrics_endpoint": f"http://{config.bot.metrics_host}:{config.bot.metrics_port}/metrics",
            "metrics_http_enabled": metrics_available,
            "metrics_start_error": metrics_start_error,
        },
    )
    registry.set_gauge("live_execution_enabled", 1.0 if config.bot.live_execution_enabled else 0.0)
    registry.set_gauge("metrics_http_enabled", 1.0 if metrics_available else 0.0)


def _generate_snapshot(config: AppConfig) -> MarketSnapshot:
    signal_bps = random.uniform(-20.0, 20.0)
    price = config.strategy.base_price * (1 + signal_bps / 10000)
    return MarketSnapshot(
        symbol=config.strategy.symbol,
        price=round(price, 2),
        signal_bps=round(signal_bps, 2),
        ts=datetime.now(timezone.utc).isoformat(),
    )


def _simulate_fill(signal_bps: float, order_notional: float) -> float:
    edge = abs(signal_bps) / 10000 * order_notional
    friction = order_notional * 0.0006
    noise = random.uniform(-0.6, 0.6)
    return round(edge - friction + noise, 4)


def _finish_iteration(
    started_at: float,
    registry: MetricsRegistry,
    config: AppConfig,
) -> None:
    elapsed_ms = (time.perf_counter() - started_at) * 1000
    registry.set_gauge("loop_latency_ms", round(elapsed_ms, 3))
    time.sleep(config.bot.loop_interval_ms / 1000)


def _resolve_data_dir(config_path: Path, raw_data_dir: Path) -> Path:
    if raw_data_dir.is_absolute():
        resolved = raw_data_dir
    else:
        resolved = (config_path.parents[2] / raw_data_dir).resolve()
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved
