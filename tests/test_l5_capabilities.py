import unittest

from levels.l3_agent import baseline_signals
from levels.l5_capabilities import capability_signals


class L5CapabilityTests(unittest.TestCase):
    def test_capability_signals_are_available(self):
        self.assertIsInstance(capability_signals(), dict)

    def test_baseline_signals_include_capability_hook(self):
        signals = baseline_signals()
        self.assertIn("coordination_score", signals)
        self.assertIn("accountability_score", signals)


if __name__ == "__main__":
    unittest.main()
