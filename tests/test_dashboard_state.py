import tempfile
import unittest
import json
from pathlib import Path

from apex.core.memory import EventMemory
from apex.dashboard.state import dashboard_state, summarize_cycles
from tests.helpers import init_repo


class DashboardStateTests(unittest.TestCase):
    def test_summarizes_started_and_finished_cycles(self):
        events = [
            {"event_type": "cycle_started", "timestamp": "2026-01-01T00:00:00Z", "data": {"title": "A"}},
            {
                "event_type": "cycle_finished",
                "timestamp": "2026-01-01T00:01:00Z",
                "data": {
                    "title": "A",
                    "accepted": True,
                    "reason": "accepted",
                    "commit_hash": "abc123",
                    "changed_paths": ["module.py"],
                },
            },
        ]

        cycles = summarize_cycles(events)

        self.assertEqual(len(cycles), 1)
        self.assertTrue(cycles[0]["accepted"])
        self.assertEqual(cycles[0]["changed_paths"], ["module.py"])

    def test_dashboard_state_includes_objective_repo_and_events(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            init_repo(root)
            memory = EventMemory(root / "memory" / "events.jsonl")
            memory.append("cycle_started", {"title": "A"})
            memory.append("cycle_finished", {
                "title": "A",
                "accepted": False,
                "reason": "verification_failed",
                "changed_paths": ["module.py"],
            })

            state = dashboard_state(root)

            self.assertEqual(state["objective"]["target_level"], 5)
            self.assertEqual(state["repo"]["tracked_file_count"], 2)
            self.assertEqual(len(state["events"]), 2)
            self.assertEqual(state["cycles"][0]["reason"], "verification_failed")

    def test_dashboard_state_includes_pending_plan(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            init_repo(root)
            pending_path = root / "memory" / "pending_plan.json"
            pending_path.parent.mkdir(parents=True, exist_ok=True)
            pending_path.write_text(json.dumps({
                "goal": "Improve verification",
                "plan": {
                    "title": "Tighten verifier",
                    "operations": [],
                },
            }), encoding="utf-8")

            state = dashboard_state(root)

            self.assertEqual(state["pending_plan"]["goal"], "Improve verification")
            self.assertEqual(state["pending_plan"]["plan"]["title"], "Tighten verifier")


if __name__ == "__main__":
    unittest.main()
