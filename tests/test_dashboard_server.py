import os
import unittest
from unittest.mock import patch

from apex.dashboard.server import max_repair_attempts


class DashboardServerTests(unittest.TestCase):
    def test_default_repair_attempts(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(max_repair_attempts(), 2)

    def test_configured_repair_attempts(self):
        with patch.dict(os.environ, {"APEX_REPAIR_ATTEMPTS": "4"}):
            self.assertEqual(max_repair_attempts(), 4)

    def test_invalid_repair_attempts_falls_back(self):
        with patch.dict(os.environ, {"APEX_REPAIR_ATTEMPTS": "bad"}):
            self.assertEqual(max_repair_attempts(), 2)


if __name__ == "__main__":
    unittest.main()
