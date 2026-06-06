import unittest

from levels.l3_agent import baseline_signals
from metrics import assess_capabilities, identify_largest_gap


class MetricsTests(unittest.TestCase):
    def test_assessment_returns_bounded_scores(self):
        scores = assess_capabilities(baseline_signals())
        self.assertGreaterEqual(scores.l3_agent, 0.0)
        self.assertLessEqual(scores.l3_agent, 1.0)
        self.assertGreaterEqual(scores.aggregate, 0.0)
        self.assertLessEqual(scores.aggregate, 1.0)

    def test_gap_is_named(self):
        scores = assess_capabilities(baseline_signals())
        self.assertIn("L", identify_largest_gap(scores))


if __name__ == "__main__":
    unittest.main()
