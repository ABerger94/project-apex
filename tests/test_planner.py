import json
import tempfile
import unittest
from pathlib import Path

from apex.core.planner import OllamaPlanner, build_goal_suggestion_prompt, build_planner_prompt
from apex.core.context import read_repo_context
from apex.core.memory import EventMemory
from tests.helpers import init_repo


class FakeTransport:
    def __init__(self, response, models=None):
        self.response = response
        self.models = models or []
        self.calls = []

    def generate(self, endpoint, payload, headers, timeout_seconds):
        self.calls.append({
            "endpoint": endpoint,
            "payload": payload,
            "headers": headers,
            "timeout_seconds": timeout_seconds,
        })
        return self.response

    def list_models(self, endpoint, timeout_seconds):
        self.calls.append({
            "endpoint": endpoint,
            "payload": None,
            "headers": {},
            "timeout_seconds": timeout_seconds,
        })
        return self.models


class TimeoutTransport(FakeTransport):
    def generate(self, endpoint, payload, headers, timeout_seconds):
        raise TimeoutError("timed out")


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
            self.assertIn("Shell commands are allowed only as verification_command", prompt)

    def test_prompt_includes_recent_memory_events(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            init_repo(root)
            memory = EventMemory(root / "memory" / "events.jsonl")
            memory.append("plan_generated", {
                "title": "Add insights module",
                "target": "apex/core/insights.py",
                "operation_count": 2,
            })
            memory.append("cycle_finished", {
                "title": "Add insights module",
                "accepted": False,
                "reason": "empty_git_diff",
            })
            context = read_repo_context(root)

            prompt = build_planner_prompt(context, "Improve planning", memory.read_recent())

            self.assertIn("Recent memory events:", prompt)
            self.assertIn("Add insights module", prompt)
            self.assertIn("empty_git_diff", prompt)

    def test_goal_suggestion_prompt_includes_memory_events(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            init_repo(root)
            memory = EventMemory(root / "memory" / "events.jsonl")
            memory.append("cycle_finished", {
                "title": "Add level assessment",
                "accepted": True,
                "reason": "accepted",
            })
            context = read_repo_context(root)

            prompt = build_goal_suggestion_prompt(context, memory.read_recent(), limit=3)

            self.assertIn("APEX V2 autonomy goal selector", prompt)
            self.assertIn("Add level assessment", prompt)
            self.assertIn("Required JSON schema shape", prompt)

    def test_ollama_planner_parses_goal_suggestions(self):
        response = {
            "goals": [
                {
                    "priority": 1,
                    "goal": "Add current-level assessment report",
                    "rationale": "It uses recent level assessment work to guide the next cycle.",
                }
            ]
        }
        transport = FakeTransport({"response": json.dumps(response)})
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            init_repo(root)
            planner = OllamaPlanner(
                endpoint="https://ollama.com/api/generate",
                api_key="secret",
                transport=transport,
            )

            suggestions = planner.suggest_goals(root)

            self.assertEqual(suggestions["goals"][0]["goal"], "Add current-level assessment report")

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

    def test_ollama_planner_falls_back_to_installed_local_model(self):
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
        transport = FakeTransport({"response": json.dumps(plan_json)}, models=["qwen3.6:latest"])
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            init_repo(root)
            planner = OllamaPlanner(
                model="minimax-m3",
                endpoint="http://localhost:11434/api/generate",
                transport=transport,
            )

            planner.propose(root, "Improve test evidence")

            generate_call = next(call for call in transport.calls if call["payload"])
            self.assertEqual(generate_call["payload"]["model"], "qwen3.6:latest")

    def test_ollama_planner_diagnostic_reports_model_resolution(self):
        transport = FakeTransport({"response": "{}"}, models=["qwen3.6:latest"])
        planner = OllamaPlanner(
            model="minimax-m3",
            endpoint="http://localhost:11434/api/generate",
            transport=transport,
        )

        diagnostic = planner.diagnostic()

        self.assertEqual(diagnostic["configured_model"], "minimax-m3")
        self.assertEqual(diagnostic["resolved_model"], "qwen3.6:latest")
        self.assertEqual(diagnostic["available_models"], ["qwen3.6:latest"])

    def test_ollama_planner_uses_longer_default_timeout_for_hosted_api(self):
        planner = OllamaPlanner(
            endpoint="https://ollama.com/api/generate",
            api_key="secret",
            transport=FakeTransport({"response": "{}"}),
        )

        self.assertEqual(planner.diagnostic()["timeout_seconds"], 300)

    def test_ollama_planner_reports_timeout_with_model_and_endpoint(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            init_repo(root)
            planner = OllamaPlanner(
                model="minimax-m3",
                endpoint="https://ollama.com/api/generate",
                api_key="secret",
                timeout_seconds=1,
                transport=TimeoutTransport({"response": "{}"}),
            )

            with self.assertRaisesRegex(ValueError, "Ollama planner timed out after 1s"):
                planner.propose(root, "Make a plan")

    def test_ollama_planner_keeps_cloud_model_on_local_endpoint(self):
        transport = FakeTransport({"response": "{}"}, models=["qwen3.6:latest"])
        planner = OllamaPlanner(
            model="minimax-m3:cloud",
            endpoint="http://localhost:11434/api/generate",
            transport=transport,
        )

        diagnostic = planner.diagnostic()

        self.assertEqual(diagnostic["resolved_model"], "minimax-m3:cloud")

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
