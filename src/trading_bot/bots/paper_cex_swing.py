from __future__ import annotations

import time
from datetime import datetime, timezone
from pathlib import Path

from trading_bot.core.config import AppConfig
from trading_bot.core.metrics import MetricsRegistry, MetricsServer
from trading_bot.core.recorder import EventRecorder
from trading_bot.core.risk import RiskManager
from trading_bot.core.runtime import RunLock, config_fingerprint
from trading_bot.execution.factory import build_execution_adapter
from trading_bot.market_data.factory import build_market_data_adapter


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
    market_data = build_market_data_adapter(config)
    execution = build_execution_adapter(config)

    lock_path = data_dir / "locks" / f"{config.bot.name}.lock"
    with RunLock(lock_path):
        metrics_available = metrics_server.start()
        try:
            _record_runtime_metadata(
                config,
                recorder,
                registry,
                metrics_available,
                metrics_server.start_error,
            )
            _run_loop(config, recorder, registry, risk, market_data, execution)
        finally:
            market_data.close()
            metrics_server.stop()


def _run_loop(
    config: AppConfig,
    recorder: EventRecorder,
    registry: MetricsRegistry,
    risk: RiskManager,
    market_data: object,
    execution: object,
) -> None:
    wins = 0
    losses = 0
    iteration = 0

    while True:
        if config.bot.max_iterations > 0 and iteration >= config.bot.max_iterations:
            break
        started_at = time.perf_counter()
        snapshot = market_data.get_snapshot()
        recorder.record("market_snapshots", snapshot.to_record())
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
                    "venue": snapshot.venue,
                },
            )
            registry.inc_counter("bot_holds_total")
            _finish_iteration(started_at, registry, config)
            iteration += 1
            continue

        can_trade, reason = risk.can_open_order(config.execution.order_notional)
        if not can_trade:
            recorder.record(
                "risk_events",
                {
                    "iteration": iteration,
                    "blocked_reason": reason,
                    "signal_bps": snapshot.signal_bps,
                    "venue": snapshot.venue,
                },
            )
            registry.inc_counter("risk_blocks_total")
            _finish_iteration(started_at, registry, config)
            iteration += 1
            continue

        side = "buy" if snapshot.signal_bps > 0 else "sell"
        execution_result = execution.execute(snapshot, side, config.execution.order_notional)
        risk.register_fill(config.execution.order_notional, execution_result.realized_pnl)
        if execution_result.realized_pnl >= 0:
            wins += 1
        else:
            losses += 1

        recorder.record(
            "paper_fills",
            {
                "iteration": iteration,
                **execution_result.to_record(),
                "signal_bps": snapshot.signal_bps,
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

    recorder.record(
        "reports",
        {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "wins": wins,
            "losses": losses,
            "daily_realized_pnl": risk.state.daily_realized_pnl,
            "consecutive_losses": risk.state.consecutive_losses,
            "execution_mode": config.execution.mode,
            "market_data_adapter": config.market_data.adapter,
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
            "market_data_adapter": config.market_data.adapter,
            "market_data_venue": config.market_data.venue.name,
            "execution_adapter": config.execution.adapter,
            "execution_mode": config.execution.mode,
            "credentials_ref": config.execution.credentials_ref,
            "metrics_endpoint": f"http://{config.bot.metrics_host}:{config.bot.metrics_port}/metrics",
            "metrics_http_enabled": metrics_available,
            "metrics_start_error": metrics_start_error,
        },
    )
    registry.set_gauge("execution_mode_live", 1.0 if config.execution.mode == "live" else 0.0)
    registry.set_gauge("metrics_http_enabled", 1.0 if metrics_available else 0.0)


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
