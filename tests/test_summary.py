import json
import tempfile
import unittest
from pathlib import Path

from trading_bot.research.summary import summarize_records, write_summary


def _write_event(path: Path, stream: str, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    event = {"ts": "2026-03-15T00:00:00+00:00", "stream": stream, "payload": payload}
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event) + "\n")


class SummaryTest(unittest.TestCase):
    def test_summarize_records(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root_dir = Path(tmp_dir)
            _write_event(
                root_dir / "demo" / "market_snapshots" / "2026-03-15" / "events.ndjson",
                "market_snapshots",
                {"price": 100},
            )
            _write_event(
                root_dir / "demo" / "decisions" / "2026-03-15" / "events.ndjson",
                "decisions",
                {"action": "hold"},
            )
            _write_event(
                root_dir / "demo" / "paper_fills" / "2026-03-15" / "events.ndjson",
                "paper_fills",
                {"realized_pnl": 12.5},
            )
            _write_event(
                root_dir / "demo" / "risk_events" / "2026-03-15" / "events.ndjson",
                "risk_events",
                {"blocked_reason": "position_limit"},
            )

            result = summarize_records(root_dir, "demo", ["2026-03-15"])

            self.assertEqual(result.market_snapshots, 1)
            self.assertEqual(result.holds, 1)
            self.assertEqual(result.paper_trades, 1)
            self.assertEqual(result.risk_blocks, 1)
            self.assertEqual(result.realized_pnl, 12.5)
            self.assertEqual(result.blocked_reasons, {"position_limit": 1})

    def test_write_summary_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root_dir = Path(tmp_dir)
            result = summarize_records(root_dir, "demo", [])
            output_path = root_dir / "summary.json"

            write_summary(result, output_path, "json")

            payload = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["bot_name"], "demo")
