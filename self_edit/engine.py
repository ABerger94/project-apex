from __future__ import annotations

import ast
import pprint
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from config import SandboxConfig
from core.oracle import Hypothesis
from self_edit.code_patcher import CodePatch, PatchError, apply_patch


@dataclass(frozen=True)
class EditResult:
    accepted: bool
    commit_hash: str | None
    test_output: str
    proposal_path: Path
    reason: str = ""
    changed_paths: tuple[Path, ...] = ()


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
        if self._capability_exists(hypothesis):
            return EditResult(
                accepted=False,
                commit_hash=None,
                test_output="Capability already implemented; selecting a different proposal.",
                proposal_path=self.config.proposal_dir,
                reason="already_implemented",
            )

        proposal_path = self._write_proposal(hypothesis)
        changed_paths = [proposal_path]

        try:
            implementation_result = self._apply_implementation(hypothesis)
        except PatchError as exc:
            self._git(["checkout", "--", str(proposal_path.relative_to(self.root))])
            return EditResult(
                accepted=False,
                commit_hash=None,
                test_output=str(exc),
                proposal_path=proposal_path,
                reason="patch_failed",
                changed_paths=(proposal_path,),
            )

        changed_paths.extend(implementation_result)
        test_result = self._run_tests()
        output = (test_result.stdout or "") + (test_result.stderr or "")

        if test_result.returncode != 0:
            for changed_path in changed_paths:
                self._git(["checkout", "--", str(changed_path.relative_to(self.root))])
            return EditResult(False, None, output, proposal_path, "tests_failed", tuple(changed_paths))

        self._git(["add", *[str(path.relative_to(self.root)) for path in changed_paths]])
        commit = self._git(["commit", "-m", f"APEX implementation: {hypothesis.title}"])
        if commit.returncode != 0:
            return EditResult(False, None, output + commit.stderr, proposal_path, "commit_failed", tuple(changed_paths))

        commit_hash = self._git(["rev-parse", "--short", "HEAD"]).stdout.strip()
        return EditResult(True, commit_hash or None, output, proposal_path, "accepted", tuple(changed_paths))

    def _apply_implementation(self, hypothesis: Hypothesis) -> list[Path]:
        """Apply code patches from hypothesis.code_changes, then update CAPABILITIES index."""
        changed_paths: list[Path] = []

        for change in hypothesis.code_changes:
            patch = CodePatch(
                target_file=str(change["target_file"]),
                mode=str(change.get("mode", "append")),
                code=str(change["code"]),
            )
            patched = apply_patch(self.root, patch)   # raises PatchError on failure
            changed_paths.append(patched)

        capability_path = self.root / "levels" / "l5_capabilities.py"
        capabilities = self._read_capabilities(capability_path)
        capability_id = self._slug(hypothesis.title)
        capabilities.append({
            "id": capability_id,
            "title": hypothesis.title,
            "rationale": hypothesis.rationale,
            "target_signal": hypothesis.target_signal,
            "expected_delta": round(max(0.0, min(0.12, float(hypothesis.expected_delta))), 4),
            "implemented_at": datetime.now(timezone.utc).isoformat(),
            "evidence": (
                f"Code patch applied to {[c['target_file'] for c in hypothesis.code_changes]}; "
                "tests passed; committed."
            ) if hypothesis.code_changes else "Logged by SelfEditEngine from accepted hypothesis.",
        })
        self._write_capabilities(capability_path, capabilities)
        changed_paths.append(capability_path)
        return changed_paths

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

    def _capability_exists(self, hypothesis: Hypothesis) -> bool:
        capability_path = self.root / "levels" / "l5_capabilities.py"
        capability_id = self._slug(hypothesis.title)
        return any(item.get("id") == capability_id for item in self._read_capabilities(capability_path))

    def _read_capabilities(self, path: Path) -> list[dict]:
        if not path.exists():
            return []
        source = path.read_text(encoding="utf-8")
        marker = "CAPABILITIES = "
        start = source.find(marker)
        if start == -1:
            return []
        start += len(marker)
        end = source.find("\n\n\n", start)
        if end == -1:
            return []
        try:
            value = ast.literal_eval(source[start:end].strip())
        except (SyntaxError, ValueError):
            return []
        return value if isinstance(value, list) else []

    def _write_capabilities(self, path: Path, capabilities: list[dict]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        body = pprint.pformat(capabilities, sort_dicts=True, width=100)
        path.write_text(
            "\n".join([
                "from __future__ import annotations",
                "",
                "",
                f"CAPABILITIES = {body}",
                "",
                "",
                "def capability_signals() -> dict[str, float]:",
                "    signals: dict[str, float] = {}",
                "    for capability in CAPABILITIES:",
                "        signal = str(capability.get(\"target_signal\", \"\"))",
                "        if not signal:",
                "            continue",
                "        delta = float(capability.get(\"expected_delta\", 0.0))",
                "        signals[signal] = min(1.0, signals.get(signal, 0.0) + max(0.0, delta))",
                "    return signals",
                "",
            ]),
            encoding="utf-8",
        )

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
