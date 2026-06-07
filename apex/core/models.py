from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime, timezone


@dataclass(frozen=True)
class FileOperation:
    kind: str
    path: str
    content: str = ""
    old: str = ""
    new: str = ""


@dataclass(frozen=True)
class ChangePlan:
    title: str
    rationale: str
    target: str
    operations: tuple[FileOperation, ...]
    verification_command: tuple[str, ...] = ("python", "-m", "unittest", "discover", "-s", "tests")


@dataclass(frozen=True)
class RepoContext:
    root: Path
    branch: str
    status: tuple[str, ...]
    tracked_files: tuple[str, ...]
    recent_commits: tuple[str, ...]
    objective_directive: str = ""


@dataclass(frozen=True)
class PatchResult:
    changed_paths: tuple[Path, ...]


@dataclass(frozen=True)
class VerificationResult:
    command: tuple[str, ...]
    returncode: int
    stdout: str
    stderr: str
    passed: bool
    checks: tuple[dict, ...] = ()


@dataclass(frozen=True)
class EvaluationResult:
    accepted: bool
    reason: str
    evidence: dict = field(default_factory=dict)


@dataclass(frozen=True)
class CycleResult:
    accepted: bool
    reason: str
    title: str
    changed_paths: tuple[str, ...]
    commit_hash: str | None
    verification: VerificationResult
    evaluation: EvaluationResult


@dataclass(frozen=True)
class ExecutionResult:
    command: tuple[str, ...]
    returncode: int
    stdout: str
    stderr: str
    duration_seconds: float
    timed_out: bool = False

    @property
    def passed(self) -> bool:
        return self.returncode == 0 and not self.timed_out


@dataclass(frozen=True)
class MemoryEvent:
    event_type: str
    data: dict
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
