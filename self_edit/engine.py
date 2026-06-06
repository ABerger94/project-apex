from __future__ import annotations

import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from config import SandboxConfig
from core.oracle import Hypothesis


@dataclass(frozen=True)
class EditResult:
    accepted: bool
    commit_hash: str | None
    test_output: str
    proposal_path: Path
    reason: str = ""


class SelfEditEngine:
    def __init__(self, root: Path, config: SandboxConfig) -> None:
        self.root = root
        self.config = config
        self.config.proposal_dir.mkdir(parents=True, exist_ok=True)

    def apply_and_verify(self, hypothesis: Hypothesis) -> EditResult:
        duplicate_path = self._find_duplicate_proposal(hypothesis)
        if duplicate_path:
            return EditResult(
                accepted=False,
                commit_hash=None,
                test_output="Duplicate proposal rejected before sandbox execution.",
                proposal_path=duplicate_path,
                reason="duplicate_proposal",
            )

        proposal_path = self._write_proposal(hypothesis)
        test_result = self._run_tests()
        output = (test_result.stdout or "") + (test_result.stderr or "")

        if test_result.returncode != 0:
            self._git(["checkout", "--", str(proposal_path.relative_to(self.root))])
            return EditResult(False, None, output, proposal_path, "tests_failed")

        self._git(["add", str(proposal_path.relative_to(self.root))])
        commit = self._git(["commit", "-m", f"APEX proposal: {hypothesis.title}"])
        if commit.returncode != 0:
            return EditResult(False, None, output + commit.stderr, proposal_path, "commit_failed")

        commit_hash = self._git(["rev-parse", "--short", "HEAD"]).stdout.strip()
        return EditResult(True, commit_hash or None, output, proposal_path, "accepted")

    def _write_proposal(self, hypothesis: Hypothesis) -> Path:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        path = self.config.proposal_dir / f"{stamp}_{self._slug(hypothesis.title)}.md"
        path.write_text(self._proposal_body(hypothesis), encoding="utf-8")
        return path

    def _find_duplicate_proposal(self, hypothesis: Hypothesis) -> Path | None:
        expected = self._proposal_body(hypothesis)
        for path in sorted(self.config.proposal_dir.glob("*.md")):
            try:
                if path.read_text(encoding="utf-8") == expected:
                    return path
            except OSError:
                continue
        return None

    def _proposal_body(self, hypothesis: Hypothesis) -> str:
        return "\n".join([
            f"# {hypothesis.title}",
            "",
            f"Rationale: {hypothesis.rationale}",
            f"Target signal: {hypothesis.target_signal}",
            f"Expected delta: {hypothesis.expected_delta}",
            "",
            "```text",
            hypothesis.proposed_patch,
            "```",
            "",
        ])

    def _run_tests(self) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            list(self.config.test_command),
            cwd=self.root,
            text=True,
            capture_output=True,
            timeout=self.config.timeout_seconds,
            check=False,
        )

    def _git(self, args: list[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", *args],
            cwd=self.root,
            text=True,
            capture_output=True,
            check=False,
        )

    @staticmethod
    def _slug(value: str) -> str:
        safe = "".join(ch.lower() if ch.isalnum() else "-" for ch in value)
        return "-".join(part for part in safe.split("-") if part)[:60] or "proposal"
