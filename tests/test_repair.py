import unittest

from core.repair import (
    FailureClass,
    RepairAction,
    classify_failure,
    choose_repair,
)


class ClassifyFailureTests(unittest.TestCase):
    def test_duplicate_proposal(self):
        self.assertEqual(classify_failure("duplicate_proposal"), FailureClass.DUPLICATE)

    def test_already_implemented(self):
        self.assertEqual(classify_failure("already_implemented"), FailureClass.CAPABILITY_EXISTS)

    def test_tests_failed(self):
        self.assertEqual(classify_failure("tests_failed"), FailureClass.TEST_FAILURE)

    def test_commit_failed(self):
        self.assertEqual(classify_failure("commit_failed"), FailureClass.COMMIT_FAILURE)

    def test_unknown_reason(self):
        self.assertEqual(classify_failure("some_random_reason"), FailureClass.UNKNOWN)

    def test_empty_string(self):
        self.assertEqual(classify_failure(""), FailureClass.UNKNOWN)


class ChooseRepairTests(unittest.TestCase):
    def test_duplicate_returns_shift_signal(self):
        repair = choose_repair(
            FailureClass.DUPLICATE,
            current_signal="coordination_score",
            current_gap="L5 organizational coordination",
            tried_signals={"coordination_score"},
        )
        self.assertIsInstance(repair, RepairAction)
        self.assertEqual(repair.strategy, "shift_signal")
        self.assertIsNotNone(repair.new_target_signal)
        self.assertNotEqual(repair.new_target_signal, "coordination_score")

    def test_duplicate_avoids_all_tried_signals(self):
        tried = {"coordination_score", "accountability_score", "measured_gain"}
        repair = choose_repair(
            FailureClass.DUPLICATE,
            current_signal="coordination_score",
            current_gap="L5 organizational coordination",
            tried_signals=tried,
        )
        self.assertNotIn(repair.new_target_signal, tried)

    def test_capability_exists_advances_gap(self):
        repair = choose_repair(
            FailureClass.CAPABILITY_EXISTS,
            current_signal="coordination_score",
            current_gap="L5 organizational coordination",
            tried_signals=set(),
        )
        self.assertEqual(repair.strategy, "advance_gap")
        self.assertIsNotNone(repair.new_gap_override)
        self.assertNotEqual(repair.new_gap_override, "L5 organizational coordination")

    def test_capability_exists_l4_advances_to_l3(self):
        repair = choose_repair(
            FailureClass.CAPABILITY_EXISTS,
            current_signal="novelty_score",
            current_gap="L4 validated innovation",
            tried_signals=set(),
        )
        self.assertEqual(repair.new_gap_override, "L3 execution reliability")

    def test_test_failure_decomposes_l5_to_l4(self):
        repair = choose_repair(
            FailureClass.TEST_FAILURE,
            current_signal="coordination_score",
            current_gap="L5 organizational coordination",
            tried_signals={"coordination_score"},
        )
        self.assertEqual(repair.strategy, "decompose")
        self.assertEqual(repair.new_target_signal, "measured_gain")
        self.assertIsNotNone(repair.decompose_hint)

    def test_test_failure_decomposes_l4_to_l3(self):
        repair = choose_repair(
            FailureClass.TEST_FAILURE,
            current_signal="novelty_score",
            current_gap="L4 validated innovation",
            tried_signals={"novelty_score"},
        )
        self.assertEqual(repair.new_target_signal, "execution_success")

    def test_test_failure_decomposes_l3_to_verification(self):
        repair = choose_repair(
            FailureClass.TEST_FAILURE,
            current_signal="execution_success",
            current_gap="L3 execution reliability",
            tried_signals={"execution_success"},
        )
        self.assertEqual(repair.new_target_signal, "verification_coverage")

    def test_commit_failure_picks_alternate_signal(self):
        repair = choose_repair(
            FailureClass.COMMIT_FAILURE,
            current_signal="coordination_score",
            current_gap="L5 organizational coordination",
            tried_signals={"coordination_score"},
        )
        self.assertEqual(repair.strategy, "alternate_signal")
        self.assertIsNotNone(repair.new_target_signal)
        self.assertNotEqual(repair.new_target_signal, "coordination_score")

    def test_unknown_failure_simplifies(self):
        repair = choose_repair(
            FailureClass.UNKNOWN,
            current_signal="coordination_score",
            current_gap="L5 organizational coordination",
            tried_signals=set(),
        )
        self.assertEqual(repair.strategy, "simplify")

    def test_repair_rationale_is_non_empty(self):
        for fc in FailureClass:
            repair = choose_repair(fc, "coordination_score", "L5 organizational coordination", set())
            self.assertTrue(repair.rationale, f"Empty rationale for {fc}")

    def test_duplicate_no_gap_override(self):
        repair = choose_repair(
            FailureClass.DUPLICATE,
            current_signal="coordination_score",
            current_gap="L5 organizational coordination",
            tried_signals=set(),
        )
        self.assertIsNone(repair.new_gap_override)

    def test_capability_exists_no_signal_override(self):
        repair = choose_repair(
            FailureClass.CAPABILITY_EXISTS,
            current_signal="coordination_score",
            current_gap="L5 organizational coordination",
            tried_signals=set(),
        )
        self.assertIsNone(repair.new_target_signal)


if __name__ == "__main__":
    unittest.main()
