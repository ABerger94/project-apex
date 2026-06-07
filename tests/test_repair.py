import unittest

from apex.core.models import ChangePlan, CycleResult, EvaluationResult, FileOperation, VerificationResult
from apex.core.repair import build_repair_goal, should_retry_cycle, tail_text


class RepairTests(unittest.TestCase):
    def test_should_retry_verification_failure(self):
        result = cycle_result("verification_failed")

        self.assertTrue(should_retry_cycle(result))

    def test_should_not_retry_non_retryable_failure(self):
        result = cycle_result("proposal_or_log_only_change")

        self.assertFalse(should_retry_cycle(result))

    def test_repair_goal_contains_failure_evidence(self):
        plan = ChangePlan(
            title="Add failing test",
            rationale="Expose missing behavior.",
            target="tests/test_level_assessment.py",
            operations=(FileOperation(kind="append_file", path="tests/test_level_assessment.py", content="x"),),
        )
        result = cycle_result("verification_failed")

        goal = build_repair_goal("Improve assessment", plan, result, 1)

        self.assertIn("Improve assessment", goal)
        self.assertIn("Add failing test", goal)
        self.assertIn("verification_failed", goal)
        self.assertIn("ImportError", goal)
        self.assertIn("different concrete approach", goal)

    def test_tail_text_limits_large_values(self):
        self.assertEqual(tail_text("abcdef", max_chars=3), "def")


def cycle_result(reason: str) -> CycleResult:
    verification = VerificationResult(
        command=("python", "-m", "unittest"),
        returncode=1,
        stdout="ImportError: cannot import name 'assess_current_level'",
        stderr="",
        passed=False,
        checks=({"name": "test_command", "detail": "FAILED (errors=1)", "passed": False},),
    )
    return CycleResult(
        accepted=False,
        reason=reason,
        title="Failed cycle",
        changed_paths=("tests/test_level_assessment.py",),
        commit_hash=None,
        verification=verification,
        evaluation=EvaluationResult(False, reason),
    )


if __name__ == "__main__":
    unittest.main()
