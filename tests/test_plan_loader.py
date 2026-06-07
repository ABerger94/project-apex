import tempfile
import unittest
from pathlib import Path

from apex.core.models import FileOperation
from apex.core.plan_loader import load_plan, plan_from_dict


class PlanLoaderTests(unittest.TestCase):
    def test_loads_strict_json_plan(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "plan.json"
            path.write_text(
                """
                {
                  "title": "Edit code",
                  "rationale": "Make one concrete source change.",
                  "target": "module.py",
                  "operations": [
                    {"kind": "replace_text", "path": "module.py", "old": "VALUE = 1", "new": "VALUE = 2"}
                  ],
                  "verification_command": ["python", "-m", "unittest"]
                }
                """,
                encoding="utf-8",
            )

            plan = load_plan(path)

            self.assertEqual(plan.title, "Edit code")
            self.assertEqual(plan.operations, (FileOperation(kind="replace_text", path="module.py", old="VALUE = 1", new="VALUE = 2"),))
            self.assertEqual(plan.verification_command, ("python", "-m", "unittest"))

    def test_rejects_missing_operations(self):
        with self.assertRaises(ValueError):
            plan_from_dict({
                "title": "No work",
                "rationale": "This is vague.",
                "target": "none",
                "operations": [],
            })

    def test_rejects_malformed_operation(self):
        with self.assertRaises(ValueError):
            plan_from_dict({
                "title": "Bad write",
                "rationale": "Content is required for writes.",
                "target": "module.py",
                "operations": [{"kind": "write_file", "path": "module.py"}],
            })


if __name__ == "__main__":
    unittest.main()

