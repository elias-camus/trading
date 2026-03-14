from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class BotRuntimeConfig:
    name: str
    environment: str
    data_dir: Path
    metrics_host: str
    metrics_port: int
    loop_interval_ms: int
    max_iterations: int
    live_execution_enabled: bool


@dataclass
class RiskConfig:
    max_position_notional: float
    max_daily_loss: float
    max_consecutive_losses: int
    min_order_interval_seconds: int


@dataclass
class SwingStrategyConfig:
    symbol: str
    base_price: float
    signal_threshold_bps: float
    order_notional: float


@dataclass
class AppConfig:
    bot: BotRuntimeConfig
    risk: RiskConfig
    strategy: SwingStrategyConfig

    @classmethod
    def load(cls, path: Path) -> "AppConfig":
        raw = json.loads(path.read_text())
        return cls(
            bot=BotRuntimeConfig(
                name=raw["bot"]["name"],
                environment=raw["bot"]["environment"],
                data_dir=Path(raw["bot"]["data_dir"]),
                metrics_host=raw["bot"]["metrics_host"],
                metrics_port=int(raw["bot"]["metrics_port"]),
                loop_interval_ms=int(raw["bot"]["loop_interval_ms"]),
                max_iterations=int(raw["bot"]["max_iterations"]),
                live_execution_enabled=bool(raw["bot"]["live_execution_enabled"]),
            ),
            risk=RiskConfig(
                max_position_notional=float(raw["risk"]["max_position_notional"]),
                max_daily_loss=float(raw["risk"]["max_daily_loss"]),
                max_consecutive_losses=int(raw["risk"]["max_consecutive_losses"]),
                min_order_interval_seconds=int(raw["risk"]["min_order_interval_seconds"]),
            ),
            strategy=SwingStrategyConfig(
                symbol=raw["strategy"]["symbol"],
                base_price=float(raw["strategy"]["base_price"]),
                signal_threshold_bps=float(raw["strategy"]["signal_threshold_bps"]),
                order_notional=float(raw["strategy"]["order_notional"]),
            ),
        )
