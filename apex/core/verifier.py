from __future__ import annotations

import os
from pathlib import Path

from apex.core.executor import AllowlistedExecutor
from apex.core.models import VerificationResult


class Verifier:
    def __init__(self, root: Path, timeout_seconds: int = 60) -> None:
        self.root = root
        self.timeout_seconds = timeout_seconds

    def run(self, command: tuple[str, ...], changed_paths: tuple[Path, ...] = ()) -> VerificationResult:
        env = {
            **os.environ,
            "APEX_TEST_MODE": "1",
            "APEX_ORACLE_PROVIDER": "local",
            "APEX_REMOTE_ORACLE_MODE": "outer",
        }
        checks: list[dict] = []
        executor = AllowlistedExecutor(self.root, timeout_seconds=self.timeout_seconds)
        for path in changed_paths:
            if path.suffix != ".py":
                continue
            syntax_command = (command[0], "-m", "py_compile", str(path.relative_to(self.root)))
            syntax = executor.run(syntax_command, env=env)
            checks.append({
                "name": f"syntax:{path.relative_to(self.root)}",
                "passed": syntax.passed,
                "detail": "ok" if syntax.passed else (syntax.stderr or syntax.stdout).strip(),
            })
            if not syntax.passed:
                return VerificationResult(
                    command=command,
                    returncode=syntax.returncode,
                    stdout=syntax.stdout,
                    stderr=syntax.stderr,
                    passed=False,
                    checks=tuple(checks),
                )

        result = executor.run(command, env=env)
        checks.append({
            "name": "test_command",
            "passed": result.passed,
            "detail": self._summarize_output(result.stdout + result.stderr),
        })
        return VerificationResult(
            command=command,
            returncode=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
            passed=result.passed and all(check["passed"] for check in checks),
            checks=tuple(checks),
        )

    @staticmethod
    def _summarize_output(output: str) -> str:
        lines = [line.strip() for line in output.splitlines() if line.strip()]
        if not lines:
            return "no output"
        for line in reversed(lines):
            if line == "OK" or "FAILED" in line or line.startswith("Ran "):
                return line
        return lines[-1]
