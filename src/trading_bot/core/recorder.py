from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class EventRecorder:
    root_dir: Path
    bot_name: str

    def __post_init__(self) -> None:
        self.root_dir.mkdir(parents=True, exist_ok=True)

    def record(self, stream: str, payload: dict[str, Any]) -> Path:
        now = datetime.now(timezone.utc)
        day_dir = self.root_dir / self.bot_name / stream / now.strftime("%Y-%m-%d")
        day_dir.mkdir(parents=True, exist_ok=True)
        out_file = day_dir / "events.ndjson"
        event = {
            "ts": now.isoformat(),
            "stream": stream,
            "payload": payload,
        }
        with out_file.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, sort_keys=True) + "\n")
        return out_file
