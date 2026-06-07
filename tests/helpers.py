from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def run_git(root: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=root, text=True, capture_output=True, check=False)


def init_repo(root: Path) -> None:
    run_git(root, ["init"])
    run_git(root, ["config", "user.email", "apex-v2@example.test"])
    run_git(root, ["config", "user.name", "APEX V2 Tests"])
    (root / "tests").mkdir(parents=True, exist_ok=True)
    (root / "tests" / "test_smoke.py").write_text(
        "import unittest\n\n\nclass SmokeTests(unittest.TestCase):\n    def test_smoke(self):\n        self.assertTrue(True)\n\n",
        encoding="utf-8",
    )
    (root / "module.py").write_text("VALUE = 1\n", encoding="utf-8")
    run_git(root, ["add", "."])
    commit = run_git(root, ["commit", "-m", "initial"])
    if commit.returncode != 0:
        raise RuntimeError(commit.stderr or commit.stdout)


def python_test_command() -> tuple[str, ...]:
    return (sys.executable, "-m", "unittest", "discover", "-s", "tests")

