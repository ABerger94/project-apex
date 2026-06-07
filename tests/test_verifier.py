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
                root = Path(temp_dir)
                (root / "tests").mkdir()
                (root / "tests" / "test_env.py").write_text(
                    "import os\nimport unittest\n\n\n"
                    "class EnvTests(unittest.TestCase):\n"
                    "    def test_oracle_env_is_isolated(self):\n"
                    "        self.assertEqual(os.getenv('APEX_ORACLE_PROVIDER'), 'local')\n"
                    "        self.assertEqual(os.getenv('APEX_REMOTE_ORACLE_MODE'), 'outer')\n",
                    encoding="utf-8",
                )
                result = Verifier(root).run((sys.executable, "-m", "unittest", "discover", "-s", "tests"))

            self.assertTrue(result.passed)
            self.assertIn("OK", result.stdout + result.stderr)
        finally:
            if previous_provider is None:
                os.environ.pop("APEX_ORACLE_PROVIDER", None)
            else:
                os.environ["APEX_ORACLE_PROVIDER"] = previous_provider
            if previous_mode is None:
                os.environ.pop("APEX_REMOTE_ORACLE_MODE", None)
            else:
                os.environ["APEX_REMOTE_ORACLE_MODE"] = previous_mode

    def test_verifier_fails_fast_on_changed_python_syntax_error(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            bad_file = root / "bad.py"
            bad_file.write_text("def broken(:\n", encoding="utf-8")

            result = Verifier(root).run(
                (sys.executable, "-m", "unittest", "discover", "-s", "tests"),
                changed_paths=(bad_file,),
            )

            self.assertFalse(result.passed)
            self.assertEqual(result.checks[0]["name"], "syntax:bad.py")
            self.assertFalse(result.checks[0]["passed"])


if __name__ == "__main__":
    unittest.main()
