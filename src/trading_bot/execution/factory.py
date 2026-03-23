from __future__ import annotations

from trading_bot.core.config import AppConfig
from trading_bot.core.secrets import resolve_credentials
from trading_bot.execution.base import ExecutionAdapter
from trading_bot.execution.bitflyer import BitFlyerExecutionAdapter
from trading_bot.execution.dry_run import DryRunExecutionAdapter
from trading_bot.execution.moomoo import MoomooExecutionAdapter
from trading_bot.execution.paper import PaperExecutionAdapter


def build_execution_adapter(config: AppConfig) -> ExecutionAdapter:
    adapter = config.execution.adapter
    if adapter == "paper":
        return PaperExecutionAdapter()
    if adapter == "dry-run":
        return DryRunExecutionAdapter()
    if adapter == "bitflyer-dry-run":
        credentials = _resolve_execution_credentials(config)
        return BitFlyerExecutionAdapter(
            api_key=credentials.api_key,
            api_secret=credentials.api_secret,
            mode="dry-run",
        )
    if adapter == "bitflyer-live":
        credentials = _resolve_execution_credentials(config)
        return BitFlyerExecutionAdapter(
            api_key=credentials.api_key,
            api_secret=credentials.api_secret,
            mode="live",
        )
    if adapter == "moomoo-dry-run":
        credentials = _resolve_execution_credentials(config)
        return MoomooExecutionAdapter(
            trade_unlock_pwd=credentials.api_secret,
            mode="dry-run",
        )
    if adapter == "moomoo-live":
        import moomoo
        credentials = _resolve_execution_credentials(config)
        return MoomooExecutionAdapter(
            trade_unlock_pwd=credentials.api_secret,
            mode="live",
            trd_env=moomoo.TrdEnv.REAL,
        )
    if adapter == "live":
        raise NotImplementedError("Live execution adapter is not implemented yet")
    raise ValueError(f"Unsupported execution adapter: {adapter}")


def _resolve_execution_credentials(config: AppConfig):
    credentials_ref = config.execution.credentials_ref
    if credentials_ref is None:
        raise ValueError("BitFlyer execution adapter requires execution.credentials_ref")
    try:
        credentials_config = config.credentials[credentials_ref]
    except KeyError as exc:
        raise ValueError(
            f"Execution credentials_ref was not found: {credentials_ref}"
        ) from exc
    return resolve_credentials(credentials_config)
