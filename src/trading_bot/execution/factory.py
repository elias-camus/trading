from __future__ import annotations

from trading_bot.core.config import AppConfig
from trading_bot.execution.base import ExecutionAdapter
from trading_bot.execution.dry_run import DryRunExecutionAdapter
from trading_bot.execution.paper import PaperExecutionAdapter


def build_execution_adapter(config: AppConfig) -> ExecutionAdapter:
    adapter = config.execution.adapter
    if adapter == "paper":
        return PaperExecutionAdapter()
    if adapter == "dry-run":
        return DryRunExecutionAdapter()
    if adapter == "live":
        raise ValueError("Live execution adapter is not implemented yet")
    raise ValueError(f"Unsupported execution adapter: {adapter}")
