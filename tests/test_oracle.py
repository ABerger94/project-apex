import unittest

from core.oracle import LocalOracle
from metrics import CapabilityScores


class OracleTests(unittest.TestCase):
    def test_local_oracle_returns_actionable_hypothesis(self):
        hypothesis = LocalOracle().propose(CapabilityScores(0.4, 0.2, 0.1), "L3 execution reliability")
        self.assertTrue(hypothesis.title)
        self.assertGreater(hypothesis.expected_delta, 0)
        self.assertIn("Primary gap", hypothesis.proposed_patch)

    def test_local_oracle_avoids_rejected_title(self):
        hypothesis = LocalOracle().propose(
            CapabilityScores(0.4, 0.2, 0.1),
            "L5 organizational coordination",
            rejected=[{"title": "Increase benchmark observability"}],
        )
        self.assertNotEqual(hypothesis.title, "Increase benchmark observability")
        self.assertIn("L5", hypothesis.title)


if __name__ == "__main__":
    unittest.main()
