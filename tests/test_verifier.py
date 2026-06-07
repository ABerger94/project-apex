import os
import sys
import tempfile
import unittest
from pathlib import Path

from apex.core.verifier import Verifier


class VerifierTests(unittest.TestCase):
    def test_verifier_isolates_live_oracle_env(self):
        previous_provider = os.environ.get("APEX_ORACLE_PROVIDER")
        previous_mode = os.environ.get("APEX_REMOTE_ORACLE_MODE")
        try:
            os.environ["APEX_ORACLE_PROVIDER"] = "ollama"
            os.environ["APEX_REMOTE_ORACLE_MODE"] = "always"
            with tempfile.TemporaryDirectory() as temp_dir:
                result = Verifier(Path(temp_dir)).run((
                    sys.executable,
                    "-c",
                    "import os; print(os.getenv('APEX_ORACLE_PROVIDER'), os.getenv('APEX_REMOTE_ORACLE_MODE'))",
                ))

            self.assertTrue(result.passed)
            self.assertIn("local outer", result.stdout)
        finally:
            if previous_provider is None:
                os.environ.pop("APEX_ORACLE_PROVIDER", None)
            else:
                os.environ["APEX_ORACLE_PROVIDER"] = previous_provider
            if previous_mode is None:
                os.environ.pop("APEX_REMOTE_ORACLE_MODE", None)
            else:
                os.environ["APEX_REMOTE_ORACLE_MODE"] = previous_mode


if __name__ == "__main__":
    unittest.main()

