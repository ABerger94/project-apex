from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


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

