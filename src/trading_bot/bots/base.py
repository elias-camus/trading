from __future__ import annotations

import time
from abc import ABC, abstractmethod
from pathlib import Path

from trading_bot.core.config import AppConfig
from trading_bot.core.metrics import MetricsRegistry, MetricsServer
from trading_bot.core.recorder import EventRecorder
from trading_bot.core.risk import RiskManager
from trading_bot.core.runtime import RunLock, config_fingerprint
from trading_bot.execution.base import ExecutionAdapter
from trading_bot.execution.factory import build_execution_adapter
from trading_bot.market_data.base import MarketDataAdapter
from trading_bot.market_data.factory import build_market_data_adapter


class BaseBot(ABC):
    def __init__(self, config_path: Path) -> None:
        self.config_path = config_path
        self.config = AppConfig.load(config_path)
        self.data_dir = self._resolve_data_dir(config_path, self.config.bot.data_dir)
        self.registry = MetricsRegistry()
        self.recorder = EventRecorder(
            root_dir=self.data_dir / "records",
            bot_name=self.config.bot.name,
        )
        self.risk = RiskManager(self.config.risk)
        self.metrics_server = MetricsServer(
            self.config.bot.metrics_host,
            self.config.bot.metrics_port,
            self.registry,
        )
        self.market_data = self.build_market_data_adapter()
        self.execution = self.build_execution_adapter()

    def build_market_data_adapter(self) -> MarketDataAdapter:
        return build_market_data_adapter(self.config)

    def build_execution_adapter(self) -> ExecutionAdapter:
        return build_execution_adapter(self.config)

    def run(self) -> None:
        lock_path = self.data_dir / "locks" / f"{self.config.bot.name}.lock"
        with RunLock(lock_path):
            metrics_available = self.metrics_server.start()
            try:
                self._record_runtime_metadata(
                    metrics_available,
                    self.metrics_server.start_error,
                )
                self.before_loop()
                self._run_loop()
                self.after_loop()
            finally:
                self.market_data.close()
                self.metrics_server.stop()

    def before_loop(self) -> None:
        return

    @abstractmethod
    def run_iteration(self, iteration: int) -> None:
        raise NotImplementedError

    def after_loop(self) -> None:
        return

    def _run_loop(self) -> None:
        iteration = 0
        while not self.should_stop(iteration):
            started_at = time.perf_counter()
            self.run_iteration(iteration)
            self._finish_iteration(started_at)
            iteration += 1

    def should_stop(self, iteration: int) -> bool:
        max_iterations = self.config.bot.max_iterations
        return max_iterations > 0 and iteration >= max_iterations

    def _record_runtime_metadata(
        self,
        metrics_available: bool,
        metrics_start_error: str | None,
    ) -> None:
        self.recorder.record(
            "runtime",
            {
                "bot_name": self.config.bot.name,
                "environment": self.config.bot.environment,
                "config_fingerprint": config_fingerprint(self.config),
                "market_data_adapter": self.config.market_data.adapter,
                "market_data_venue": self.config.market_data.venue.name,
                "execution_adapter": self.config.execution.adapter,
                "execution_mode": self.config.execution.mode,
                "credentials_ref": self.config.execution.credentials_ref,
                "metrics_endpoint": (
                    f"http://{self.config.bot.metrics_host}:{self.config.bot.metrics_port}/metrics"
                ),
                "metrics_http_enabled": metrics_available,
                "metrics_start_error": metrics_start_error,
            },
        )
        self.registry.set_gauge(
            "execution_mode_live",
            1.0 if self.config.execution.mode == "live" else 0.0,
        )
        self.registry.set_gauge("metrics_http_enabled", 1.0 if metrics_available else 0.0)

    def _finish_iteration(self, started_at: float) -> None:
        elapsed_ms = (time.perf_counter() - started_at) * 1000
        self.registry.set_gauge("loop_latency_ms", round(elapsed_ms, 3))
        time.sleep(self.config.bot.loop_interval_ms / 1000)

    @staticmethod
    def _resolve_data_dir(config_path: Path, raw_data_dir: Path) -> Path:
        if raw_data_dir.is_absolute():
            resolved = raw_data_dir
        else:
            resolved = (config_path.parents[2] / raw_data_dir).resolve()
        resolved.mkdir(parents=True, exist_ok=True)
        return resolved
