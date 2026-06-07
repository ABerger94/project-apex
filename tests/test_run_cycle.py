import tempfile
import unittest
from pathlib import Path

from apex.core.models import ChangePlan, FileOperation
from apex.run_cycle import run_manual_cycle
from tests.helpers import init_repo, python_test_command, run_git


class RunCycleTests(unittest.TestCase):
    def test_cycle_commits_functional_change_when_tests_pass(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            init_repo(root)
            plan = ChangePlan(
                title="Raise module value",
                rationale="A minimal functional source edit proves the commit gate.",
                target="module.py",
                operations=(FileOperation(kind="replace_text", path="module.py", old="VALUE = 1", new="VALUE = 2"),),
                verification_command=python_test_command(),
            )

            result = run_manual_cycle(root, plan)

            self.assertTrue(result.accepted)
            self.assertEqual(result.reason, "accepted")
            self.assertIsNotNone(result.commit_hash)
            self.assertIn("VALUE = 2", (root / "module.py").read_text(encoding="utf-8"))
            self.assertIn("APEX V2 improvement: Raise module value", run_git(root, ["log", "-1", "--pretty=%s"]).stdout)

    def test_cycle_rolls_back_proposal_only_change(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            init_repo(root)
            plan = ChangePlan(
                title="Write proposal only",
                rationale="Proposal artifacts cannot count as self-improvement.",
                target="self_edit/proposals/idea.md",
                operations=(FileOperation(kind="write_file", path="self_edit/proposals/idea.md", content="idea\n"),),
                verification_command=python_test_command(),
            )

            result = run_manual_cycle(root, plan)

            self.assertFalse(result.accepted)
            self.assertEqual(result.reason, "proposal_or_log_only_change")
            self.assertFalse((root / "self_edit" / "proposals" / "idea.md").exists())

    def test_cycle_commits_new_functional_files_when_tests_pass(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            init_repo(root)
            plan = ChangePlan(
                title="Add insights helper",
                rationale="New tested source files must count as concrete improvement.",
                target="insights.py",
                operations=(
                    FileOperation(
                        kind="write_file",
                        path="insights.py",
                        content="def current_level():\n    return 3\n",
                    ),
                    FileOperation(
                        kind="write_file",
                        path="tests/test_insights.py",
                        content=(
                            "import unittest\n\n"
                            "from insights import current_level\n\n\n"
                            "class InsightTests(unittest.TestCase):\n"
                            "    def test_current_level(self):\n"
                            "        self.assertEqual(current_level(), 3)\n"
                        ),
                    ),
                ),
                verification_command=python_test_command(),
            )

            result = run_manual_cycle(root, plan)

            self.assertTrue(result.accepted)
            self.assertEqual(result.reason, "accepted")
            self.assertTrue((root / "insights.py").exists())
            self.assertIn("insights.py", run_git(root, ["ls-files"]).stdout)


if __name__ == "__main__":
    unittest.main()
