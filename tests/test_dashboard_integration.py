import json
import sys
import tempfile
import threading
import unittest
import urllib.request
from dataclasses import asdict
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

from apex.core.models import ChangePlan, FileOperation
from apex.dashboard.server import DashboardHandler
from tests.helpers import init_repo


class FakePlanner:
    def diagnostic(self):
        return {"configured_model": "fake", "resolved_model": "fake", "timeout_seconds": 1}

    def propose(self, root, goal):
        return ChangePlan(
            title="Raise module value",
            rationale="A concrete source edit for integration coverage.",
            target="module.py",
            operations=(FileOperation(kind="replace_text", path="module.py", old="VALUE = 1", new="VALUE = 2"),),
            verification_command=(sys.executable, "-m", "unittest", "discover", "-s", "tests"),
        )

    def suggest_goals(self, root):
        return {"goals": [{"priority": 1, "goal": "Raise module value", "rationale": "It is testable."}]}


class DashboardIntegrationTests(unittest.TestCase):
    def test_generate_and_run_pending_plan_over_http(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            init_repo(root)
            with running_dashboard(root) as base_url, patch("apex.dashboard.server.OllamaPlanner", FakePlanner):
                generated = post_json(base_url + "/api/generate-plan", {"goal": "Improve module"})

                self.assertEqual(generated["pending_plan"]["plan"]["title"], "Raise module value")
                self.assertIn("preview", generated["state"]["pending_plan"])

                result = post_json(base_url + "/api/run-pending-plan")

                self.assertTrue(result["result"]["accepted"])
                self.assertEqual((root / "module.py").read_text(encoding="utf-8"), "VALUE = 2\n")
                self.assertIsNone(result["state"]["pending_plan"])

    def test_dry_run_pending_plan_over_http_does_not_mutate_repo(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            init_repo(root)
            pending_path = root / "memory" / "pending_plan.json"
            pending_path.parent.mkdir(parents=True, exist_ok=True)
            plan = FakePlanner().propose(root, "Improve module")
            pending_path.write_text(json.dumps({"goal": "Improve module", "plan": asdict(plan)}, indent=2), encoding="utf-8")

            with running_dashboard(root) as base_url, patch("apex.dashboard.server.OllamaPlanner", FakePlanner):
                result = post_json(base_url + "/api/dry-run-pending-plan")

                self.assertTrue(result["result"]["accepted"])
                self.assertEqual((root / "module.py").read_text(encoding="utf-8"), "VALUE = 1\n")
                self.assertIsNotNone(result["state"]["pending_plan"])


class running_dashboard:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.server = None
        self.thread = None
        self.previous_root = None

    def __enter__(self) -> str:
        import apex.dashboard.server as server_module

        self.previous_root = server_module.ROOT
        server_module.ROOT = self.root
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), DashboardHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        host, port = self.server.server_address
        return f"http://{host}:{port}"

    def __exit__(self, exc_type, exc, tb) -> None:
        import apex.dashboard.server as server_module

        if self.server:
            self.server.shutdown()
            self.server.server_close()
        if self.thread:
            self.thread.join(timeout=5)
        if self.previous_root is not None:
            server_module.ROOT = self.previous_root


def post_json(url: str, payload: dict | None = None) -> dict:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload or {}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


if __name__ == "__main__":
    unittest.main()
