import json
import tempfile
import unittest
from pathlib import Path

from trading_bot.core.recorder import EventRecorder


class EventRecorderTest(unittest.TestCase):
    def test_recorder_writes_ndjson(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            recorder = EventRecorder(root_dir=Path(tmp_dir), bot_name="demo")
            out_file = recorder.record("market_snapshots", {"price": 100.0})

            lines = out_file.read_text(encoding="utf-8").strip().splitlines()
            self.assertEqual(len(lines), 1)
            event = json.loads(lines[0])
            self.assertEqual(event["stream"], "market_snapshots")
            self.assertEqual(event["payload"]["price"], 100.0)


if __name__ == "__main__":
    unittest.main()
