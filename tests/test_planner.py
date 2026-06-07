import json
import tempfile
import unittest
from pathlib import Path

from apex.core.planner import OllamaPlanner, build_planner_prompt
from apex.core.context import read_repo_context
from tests.helpers import init_repo


class FakeTransport:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def generate(self, endpoint, payload, headers, timeout_seconds):
        self.calls.append({
            "endpoint": endpoint,
            "payload": payload,
            "headers": headers,
            "timeout_seconds": timeout_seconds,
        })
        return self.response


class PlannerTests(unittest.TestCase):
    def test_prompt_includes_level_5_objective_and_repo_context(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            init_repo(root)
            context = read_repo_context(root)

            prompt = build_planner_prompt(context, "Improve the verifier")

            self.assertIn("Level 5 AGI Organizer", prompt)
            self.assertIn("module.py", prompt)
            self.assertIn("Required JSON schema shape", prompt)
            self.assertIn("Do not use shell commands", prompt)

    def test_ollama_planner_parses_strict_change_plan(self):
        plan_json = {
            "title": "Improve smoke test",
            "rationale": "Adds a concrete test improvement toward reliable verification.",
            "target": "tests/test_smoke.py",
            "operations": [
                {
                    "kind": "append_file",
                    "path": "tests/test_smoke.py",
                    "content": "\n# additional assertion\n",
                }
            ],
            "verification_command": ["python", "-m", "unittest", "discover", "-s", "tests"],
        }
        transport = FakeTransport({"response": json.dumps(plan_json)})
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            init_repo(root)
            planner = OllamaPlanner(
                model="minimax-m3",
                endpoint="https://ollama.com/api/generate",
                api_key="secret",
                transport=transport,
            )

            plan = planner.propose(root, "Improve test evidence")

            self.assertEqual(plan.title, "Improve smoke test")
            self.assertEqual(plan.operations[0].kind, "append_file")
            self.assertEqual(transport.calls[0]["payload"]["model"], "minimax-m3")
            self.assertEqual(transport.calls[0]["payload"]["format"], "json")
            self.assertIn("Authorization", transport.calls[0]["headers"])

    def test_ollama_planner_rejects_invalid_json_response(self):
        transport = FakeTransport({"response": "not json"})
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            init_repo(root)
            planner = OllamaPlanner(endpoint="http://localhost:11434/api/generate", transport=transport)

            with self.assertRaises(ValueError):
                planner.propose(root, "Make a plan")

    def test_ollama_planner_does_not_send_api_key_to_local_endpoint(self):
        plan_json = {
            "title": "Improve smoke test",
            "rationale": "Adds a concrete test improvement toward reliable verification.",
            "target": "tests/test_smoke.py",
            "operations": [
                {
                    "kind": "append_file",
                    "path": "tests/test_smoke.py",
                    "content": "\n# additional assertion\n",
                }
            ],
            "verification_command": ["python", "-m", "unittest", "discover", "-s", "tests"],
        }
        transport = FakeTransport({"response": json.dumps(plan_json)})
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            init_repo(root)
            planner = OllamaPlanner(
                endpoint="http://localhost:11434/api/generate",
                api_key="secret",
                transport=transport,
            )

            planner.propose(root, "Improve test evidence")

            self.assertNotIn("Authorization", transport.calls[0]["headers"])

    def test_ollama_planner_rejects_schema_invalid_plan(self):
        transport = FakeTransport({"response": json.dumps({"title": "No operations"})})
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            init_repo(root)
            planner = OllamaPlanner(endpoint="http://localhost:11434/api/generate", transport=transport)

            with self.assertRaises(ValueError):
                planner.propose(root, "Make a plan")


if __name__ == "__main__":
    unittest.main()
