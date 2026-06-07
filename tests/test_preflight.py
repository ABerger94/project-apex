import sys
import tempfile
import unittest
from pathlib import Path

from apex.core.models import ChangePlan, FileOperation
from apex.core.preflight import run_preflight
from tests.helpers import init_repo, python_test_command


class PreflightTests(unittest.TestCase):
    def test_rejects_non_git_root(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            plan = ChangePlan(
                title="Edit module",
                rationale="Needs a repository.",
                target="module.py",
                operations=(FileOperation(kind="write_file", path="module.py", content="VALUE = 2\n"),),
                verification_command=python_test_command(),
            )

            result = run_preflight(Path(temp_dir), plan)

            self.assertFalse(result.passed)
            self.assertEqual(result.reason, "not_a_git_repository")

    def test_rejects_dirty_planned_path(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            init_repo(root)
            (root / "module.py").write_text("VALUE = 9\n", encoding="utf-8")
            plan = ChangePlan(
                title="Edit module",
                rationale="Must not overwrite user changes.",
                target="module.py",
                operations=(FileOperation(kind="replace_text", path="module.py", old="VALUE = 1", new="VALUE = 2"),),
                verification_command=python_test_command(),
            )

            result = run_preflight(root, plan)

            self.assertFalse(result.passed)
            self.assertEqual(result.reason, "dirty_plan_paths")
            self.assertEqual(result.evidence["conflicts"], ("module.py",))

    def test_accepts_clean_repo_with_explicit_python(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            init_repo(root)
            plan = ChangePlan(
                title="Edit module",
                rationale="Clean planned path.",
                target="module.py",
                operations=(FileOperation(kind="replace_text", path="module.py", old="VALUE = 1", new="VALUE = 2"),),
                verification_command=(sys.executable, "-m", "unittest", "discover", "-s", "tests"),
            )

            result = run_preflight(root, plan)

            self.assertTrue(result.passed)
            self.assertEqual(result.reason, "passed")


if __name__ == "__main__":
    unittest.main()
