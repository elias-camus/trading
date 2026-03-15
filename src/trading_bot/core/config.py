from __future__ import annotations

import json
from dataclasses import dataclass, field
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


@dataclass
class VenueConfig:
    name: str
    kind: str
    symbol: str
    ws_url: str | None = None
    rest_url: str | None = None


@dataclass
class MarketDataConfig:
    adapter: str
    venue: VenueConfig
    poll_interval_ms: int = 0
    record_trades: bool = False
    record_orderbook: bool = False
    credentials_ref: str | None = None


@dataclass
class CredentialsConfig:
    provider: str
    api_key: str | None = None
    api_secret: str | None = None
    api_key_env: str | None = None
    api_secret_env: str | None = None
    secret_name: str | None = None
    region: str | None = None


@dataclass
class ExecutionConfig:
    mode: str
    adapter: str
    venue: VenueConfig
    order_notional: float
    credentials_ref: str | None = None


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
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass
class AppConfig:
    bot: BotRuntimeConfig
    risk: RiskConfig
    strategy: SwingStrategyConfig
    market_data: MarketDataConfig
    execution: ExecutionConfig
    credentials: dict[str, CredentialsConfig]

    @classmethod
    def load(cls, path: Path) -> "AppConfig":
        raw = json.loads(path.read_text(encoding="utf-8"))
        normalized = _normalize_legacy_shape(raw)
        return cls(
            bot=_parse_bot(normalized["bot"]),
            risk=_parse_risk(normalized["risk"]),
            strategy=_parse_strategy(normalized["strategy"]),
            market_data=_parse_market_data(normalized["market_data"]),
            execution=_parse_execution(normalized["execution"]),
            credentials=_parse_credentials(normalized.get("credentials", {})),
        )


def _parse_bot(raw: dict[str, object]) -> BotRuntimeConfig:
    return BotRuntimeConfig(
        name=str(raw["name"]),
        environment=str(raw["environment"]),
        data_dir=Path(str(raw["data_dir"])),
        metrics_host=str(raw["metrics_host"]),
        metrics_port=int(raw["metrics_port"]),
        loop_interval_ms=int(raw["loop_interval_ms"]),
        max_iterations=int(raw["max_iterations"]),
    )


def _parse_venue(raw: dict[str, object]) -> VenueConfig:
    return VenueConfig(
        name=str(raw["name"]),
        kind=str(raw["kind"]),
        symbol=str(raw["symbol"]),
        ws_url=_optional_str(raw.get("ws_url")),
        rest_url=_optional_str(raw.get("rest_url")),
    )


def _parse_market_data(raw: dict[str, object]) -> MarketDataConfig:
    return MarketDataConfig(
        adapter=str(raw["adapter"]),
        venue=_parse_venue(dict(raw["venue"])),
        poll_interval_ms=int(raw.get("poll_interval_ms", 0)),
        record_trades=bool(raw.get("record_trades", False)),
        record_orderbook=bool(raw.get("record_orderbook", False)),
        credentials_ref=_optional_str(raw.get("credentials_ref")),
    )


def _parse_execution(raw: dict[str, object]) -> ExecutionConfig:
    return ExecutionConfig(
        mode=str(raw["mode"]),
        adapter=str(raw["adapter"]),
        venue=_parse_venue(dict(raw["venue"])),
        order_notional=float(raw["order_notional"]),
        credentials_ref=_optional_str(raw.get("credentials_ref")),
    )


def _parse_risk(raw: dict[str, object]) -> RiskConfig:
    return RiskConfig(
        max_position_notional=float(raw["max_position_notional"]),
        max_daily_loss=float(raw["max_daily_loss"]),
        max_consecutive_losses=int(raw["max_consecutive_losses"]),
        min_order_interval_seconds=int(raw["min_order_interval_seconds"]),
    )


def _parse_strategy(raw: dict[str, object]) -> SwingStrategyConfig:
    return SwingStrategyConfig(
        symbol=str(raw["symbol"]),
        base_price=float(raw["base_price"]),
        signal_threshold_bps=float(raw["signal_threshold_bps"]),
        metadata={str(key): str(value) for key, value in dict(raw.get("metadata", {})).items()},
    )


def _parse_credentials(raw: dict[str, object]) -> dict[str, CredentialsConfig]:
    credentials: dict[str, CredentialsConfig] = {}
    for name, item in raw.items():
        payload = dict(item)
        credentials[str(name)] = CredentialsConfig(
            provider=str(payload["provider"]),
            api_key=_optional_str(payload.get("api_key")),
            api_secret=_optional_str(payload.get("api_secret")),
            api_key_env=_optional_str(payload.get("api_key_env")),
            api_secret_env=_optional_str(payload.get("api_secret_env")),
            secret_name=_optional_str(payload.get("secret_name")),
            region=_optional_str(payload.get("region")),
        )
    return credentials


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    return str(value)


def _normalize_legacy_shape(raw: dict[str, object]) -> dict[str, object]:
    if "market_data" in raw and "execution" in raw:
        return raw

    bot_raw = dict(raw["bot"])
    strategy_raw = dict(raw["strategy"])
    symbol = str(strategy_raw["symbol"])
    order_notional = float(strategy_raw.get("order_notional", 0.0))
    live_execution_enabled = bool(bot_raw.get("live_execution_enabled", False))
    execution_mode = "live" if live_execution_enabled else "paper"

    normalized = dict(raw)
    normalized["bot"] = {
        key: value
        for key, value in bot_raw.items()
        if key != "live_execution_enabled"
    }
    normalized["strategy"] = {
        key: value
        for key, value in strategy_raw.items()
        if key != "order_notional"
    }
    normalized["market_data"] = {
        "adapter": "synthetic",
        "venue": {
            "name": "synthetic-feed",
            "kind": "research",
            "symbol": symbol,
        },
        "poll_interval_ms": 0,
        "record_trades": False,
        "record_orderbook": False,
    }
    normalized["execution"] = {
        "mode": execution_mode,
        "adapter": "paper" if execution_mode == "paper" else "live",
        "venue": {
            "name": "paper-execution" if execution_mode == "paper" else "live-execution",
            "kind": execution_mode,
            "symbol": symbol,
        },
        "order_notional": order_notional,
    }
    normalized.setdefault("credentials", {})
    return normalized
