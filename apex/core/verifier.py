from __future__ import annotations

import os
import subprocess
from pathlib import Path

from apex.core.models import VerificationResult


class Verifier:
    def __init__(self, root: Path, timeout_seconds: int = 60) -> None:
        self.root = root
        self.timeout_seconds = timeout_seconds

    def run(self, command: tuple[str, ...]) -> VerificationResult:
        env = {
            **os.environ,
            "APEX_TEST_MODE": "1",
            "APEX_ORACLE_PROVIDER": "local",
            "APEX_REMOTE_ORACLE_MODE": "outer",
        }
        result = subprocess.run(
            list(command),
            cwd=self.root,
            text=True,
            capture_output=True,
            timeout=self.timeout_seconds,
            check=False,
            env=env,
        )
        return VerificationResult(
            command=command,
            returncode=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
            passed=result.returncode == 0,
        )

