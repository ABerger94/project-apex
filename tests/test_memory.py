import tempfile
import unittest
from pathlib import Path

from apex.core.memory import EventMemory


class MemoryTests(unittest.TestCase):
    def test_appends_and_reads_recent_events(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            memory = EventMemory(Path(temp_dir) / "memory" / "events.jsonl")

            memory.append("cycle_started", {"title": "A"})
            memory.append("cycle_finished", {"accepted": True})
            events = memory.read_recent(limit=1)

            self.assertEqual(len(events), 1)
            self.assertEqual(events[0].event_type, "cycle_finished")
            self.assertTrue(events[0].data["accepted"])


if __name__ == "__main__":
    unittest.main()

