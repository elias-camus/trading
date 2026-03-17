from __future__ import annotations

import csv
import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path


@dataclass
class SummaryResult:
    bot_name: str
    dates: list[str]
    market_snapshots: int
    holds: int
    paper_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    average_slippage_bps: float
    risk_blocks: int
    realized_pnl: float
    blocked_reasons: dict[str, int]

    def to_dict(self) -> dict[str, object]:
        return {
            "bot_name": self.bot_name,
            "dates": self.dates,
            "market_snapshots": self.market_snapshots,
            "holds": self.holds,
            "paper_trades": self.paper_trades,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "win_rate": round(self.win_rate, 4),
            "average_slippage_bps": round(self.average_slippage_bps, 4),
            "risk_blocks": self.risk_blocks,
            "realized_pnl": round(self.realized_pnl, 4),
            "blocked_reasons": self.blocked_reasons,
        }


def summarize_records(root_dir: Path, bot_name: str, dates: list[str] | None = None) -> SummaryResult:
    selected_dates = dates or _discover_dates(root_dir, bot_name)
    blocked_reasons: Counter[str] = Counter()
    market_snapshots = 0
    holds = 0
    paper_trades = 0
    winning_trades = 0
    losing_trades = 0
    risk_blocks = 0
    realized_pnl = 0.0
    slippage_total = 0.0
    slippage_count = 0

    for day in selected_dates:
        market_snapshots += _count_stream(root_dir, bot_name, "market_snapshots", day)
        holds += _count_holds(root_dir, bot_name, day)
        trade_count, trade_pnl, wins, losses, day_slippage_total, day_slippage_count = _read_trades(
            root_dir,
            bot_name,
            day,
        )
        paper_trades += trade_count
        realized_pnl += trade_pnl
        winning_trades += wins
        losing_trades += losses
        slippage_total += day_slippage_total
        slippage_count += day_slippage_count
        block_count, reasons = _read_risk_blocks(root_dir, bot_name, day)
        risk_blocks += block_count
        blocked_reasons.update(reasons)

    decided_trades = winning_trades + losing_trades
    win_rate = winning_trades / decided_trades if decided_trades > 0 else 0.0
    average_slippage_bps = slippage_total / slippage_count if slippage_count > 0 else 0.0

    return SummaryResult(
        bot_name=bot_name,
        dates=selected_dates,
        market_snapshots=market_snapshots,
        holds=holds,
        paper_trades=paper_trades,
        winning_trades=winning_trades,
        losing_trades=losing_trades,
        win_rate=win_rate,
        average_slippage_bps=average_slippage_bps,
        risk_blocks=risk_blocks,
        realized_pnl=realized_pnl,
        blocked_reasons=dict(sorted(blocked_reasons.items())),
    )


def write_summary(result: SummaryResult, output_path: Path, output_format: str) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_format == "json":
        output_path.write_text(
            json.dumps(result.to_dict(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return output_path
    if output_format == "csv":
        with output_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=[
                    "bot_name",
                    "dates",
                    "market_snapshots",
                    "holds",
                    "paper_trades",
                    "winning_trades",
                    "losing_trades",
                    "win_rate",
                    "average_slippage_bps",
                    "risk_blocks",
                    "realized_pnl",
                    "blocked_reasons",
                ],
            )
            writer.writeheader()
            payload = result.to_dict()
            payload["dates"] = ",".join(result.dates)
            payload["blocked_reasons"] = json.dumps(result.blocked_reasons, sort_keys=True)
            writer.writerow(payload)
        return output_path
    raise ValueError(f"Unsupported output format: {output_format}")


def _discover_dates(root_dir: Path, bot_name: str) -> list[str]:
    bot_dir = root_dir / bot_name
    if not bot_dir.exists():
        return []
    dates: set[str] = set()
    for event_file in bot_dir.glob("*/*/events.ndjson"):
        dates.add(event_file.parent.name)
    return sorted(dates)


def _count_stream(root_dir: Path, bot_name: str, stream: str, day: str) -> int:
    return sum(1 for _ in _read_events(root_dir, bot_name, stream, day))


def _count_holds(root_dir: Path, bot_name: str, day: str) -> int:
    count = 0
    for event in _read_events(root_dir, bot_name, "decisions", day):
        if event["payload"].get("action") == "hold":
            count += 1
    return count


def _read_trades(
    root_dir: Path,
    bot_name: str,
    day: str,
) -> tuple[int, float, int, int, float, int]:
    count = 0
    realized_pnl = 0.0
    wins = 0
    losses = 0
    slippage_total = 0.0
    slippage_count = 0
    for event in _read_events(root_dir, bot_name, "paper_fills", day):
        payload = event["payload"]
        pnl = float(payload.get("realized_pnl", 0.0))
        count += 1
        realized_pnl += pnl
        if pnl > 0:
            wins += 1
        elif pnl < 0:
            losses += 1
        metadata = payload.get("metadata", {})
        if isinstance(metadata, dict) and "slippage_bps" in metadata:
            slippage_total += float(metadata["slippage_bps"])
            slippage_count += 1
    return count, realized_pnl, wins, losses, slippage_total, slippage_count


def _read_risk_blocks(root_dir: Path, bot_name: str, day: str) -> tuple[int, Counter[str]]:
    count = 0
    reasons: Counter[str] = Counter()
    for event in _read_events(root_dir, bot_name, "risk_events", day):
        count += 1
        reason = str(event["payload"].get("blocked_reason", "unknown"))
        reasons[reason] += 1
    return count, reasons


def _read_events(root_dir: Path, bot_name: str, stream: str, day: str) -> list[dict[str, object]]:
    event_file = root_dir / bot_name / stream / day / "events.ndjson"
    if not event_file.exists():
        return []
    lines = event_file.read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]
