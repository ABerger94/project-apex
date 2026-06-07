from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path

from apex.core.models import ExecutionResult


class AllowlistedExecutor:
    def __init__(self, root: Path, allowed_prefixes: tuple[tuple[str, ...], ...] | None = None, timeout_seconds: int = 60) -> None:
        self.root = root
        self.timeout_seconds = timeout_seconds
        self.allowed_prefixes = allowed_prefixes or (
            ("python", "-m", "unittest"),
            ("python", "-m", "py_compile"),
        )

    def run(self, command: tuple[str, ...], env: dict[str, str] | None = None) -> ExecutionResult:
        self._validate(command)
        merged_env = os.environ.copy()
        if env:
            merged_env.update(env)
        start = time.perf_counter()
        try:
            result = subprocess.run(
                list(command),
                cwd=self.root,
                text=True,
                capture_output=True,
                timeout=self.timeout_seconds,
                check=False,
                env=merged_env,
            )
            return ExecutionResult(
                command=command,
                returncode=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
                duration_seconds=time.perf_counter() - start,
            )
        except subprocess.TimeoutExpired as error:
            return ExecutionResult(
                command=command,
                returncode=-1,
                stdout=error.stdout or "",
                stderr=error.stderr or f"Timed out after {self.timeout_seconds}s",
                duration_seconds=time.perf_counter() - start,
                timed_out=True,
            )

    def _validate(self, command: tuple[str, ...]) -> None:
        if not command:
            raise ValueError("Command cannot be empty")
        if any(not part or any(char in part for char in ("\n", "\r")) for part in command):
            raise ValueError("Command contains an unsafe empty or multiline argument")
        first = "python" if Path(command[0]).name.lower() in {"python.exe", "python"} else command[0]
        normalized = (first, *command[1:])
        for prefix in self.allowed_prefixes:
            if normalized[: len(prefix)] == prefix:
                return
        raise ValueError(f"Command is not allowlisted: {' '.join(command)}")
