import tempfile
import unittest
from pathlib import Path

from core.oracle import LocalOracle
from metrics import CapabilityScores


class OracleTests(unittest.TestCase):
    def test_local_oracle_returns_actionable_hypothesis(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            hypothesis = LocalOracle(Path(temp_dir) / "routes.json").propose(
                CapabilityScores(0.4, 0.2, 0.1),
                "L3 execution reliability",
            )
        self.assertTrue(hypothesis.title)
        self.assertGreater(hypothesis.expected_delta, 0)
        self.assertIn("Primary gap", hypothesis.proposed_patch)

    def test_local_oracle_avoids_rejected_title(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            hypothesis = LocalOracle(Path(temp_dir) / "routes.json").propose(
                CapabilityScores(0.4, 0.2, 0.1),
                "L5 organizational coordination",
                rejected=[{"title": "Increase benchmark observability"}],
            )
        self.assertNotEqual(hypothesis.title, "Increase benchmark observability")
        self.assertIn("L5", hypothesis.title)

    def test_local_oracle_expands_routes_when_known_routes_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            oracle = LocalOracle(Path(temp_dir) / "routes.json")
            rejected = [{"title": route["title"]} for route in oracle._default_routes()]

            hypothesis = oracle.propose(
                CapabilityScores(0.4, 0.2, 0.1),
                "L5 organizational coordination",
                rejected=rejected,
            )

            self.assertIn("Explore L5 route", hypothesis.title)
            self.assertIn("Primary gap", hypothesis.proposed_patch)


if __name__ == "__main__":
    unittest.main()
