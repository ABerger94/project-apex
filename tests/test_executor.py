import sys
import tempfile
import unittest
from pathlib import Path

from apex.core.executor import AllowlistedExecutor


class ExecutorTests(unittest.TestCase):
    def test_runs_allowlisted_python_unittest_command(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "tests").mkdir()
            (root / "tests" / "test_ok.py").write_text(
                "import unittest\n\nclass Ok(unittest.TestCase):\n    def test_ok(self):\n        self.assertTrue(True)\n",
                encoding="utf-8",
            )

            result = AllowlistedExecutor(root).run((sys.executable, "-m", "unittest", "discover", "-s", "tests"))

            self.assertTrue(result.passed)
            self.assertIn("OK", result.stdout + result.stderr)

    def test_rejects_non_allowlisted_command(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaises(ValueError):
                AllowlistedExecutor(Path(temp_dir)).run(("git", "status"))


if __name__ == "__main__":
    unittest.main()
