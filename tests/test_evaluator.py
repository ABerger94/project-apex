import tempfile
import unittest
from pathlib import Path

from apex.core.evaluator import Evaluator
from apex.core.models import ChangePlan, EvaluationResult, FileOperation, VerificationResult


class EvaluatorTests(unittest.TestCase):
    def test_rejects_proposal_only_change(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            proposal = root / "self_edit" / "proposals" / "idea.md"
            plan = ChangePlan(
                title="Proposal only",
                rationale="This must not count as self-improvement.",
                target="policy",
                operations=(FileOperation(kind="write_file", path="self_edit/proposals/idea.md", content="idea"),),
            )
            verification = VerificationResult(("python", "-m", "unittest"), 0, "OK", "", True)

            result = Evaluator().evaluate(plan, (proposal,), verification, ("self_edit/proposals/idea.md",), root)

            self.assertEqual(result, EvaluationResult(False, "proposal_or_log_only_change", {"changed_paths": ("self_edit/proposals/idea.md",)}))

    def test_accepts_functional_change_with_passing_tests_and_diff(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "module.py"
            plan = ChangePlan(
                title="Functional change",
                rationale="This changes runtime code.",
                target="module.py",
                operations=(FileOperation(kind="write_file", path="module.py", content="VALUE = 2\n"),),
            )
            verification = VerificationResult(("python", "-m", "unittest"), 0, "OK", "", True)

            result = Evaluator().evaluate(plan, (source,), verification, ("module.py",), root)

            self.assertTrue(result.accepted)
            self.assertEqual(result.reason, "accepted")
            self.assertEqual(result.evidence["functional_paths"], ("module.py",))


if __name__ == "__main__":
    unittest.main()

