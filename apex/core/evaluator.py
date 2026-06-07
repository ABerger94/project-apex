from __future__ import annotations

from pathlib import Path

from apex.core.models import ChangePlan, EvaluationResult, VerificationResult


ARTIFACT_PREFIXES = (
    "memory/",
    "logs/",
    "self_edit/proposals/",
    "proposals/",
    "reports/",
)


class Evaluator:
    def evaluate(
        self,
        plan: ChangePlan,
        changed_paths: tuple[Path, ...],
        verification: VerificationResult,
        diff_paths: tuple[str, ...],
        root: Path,
    ) -> EvaluationResult:
        relative_changed = tuple(str(path.relative_to(root)).replace("\\", "/") for path in changed_paths)
        functional_paths = tuple(path for path in relative_changed if not self._is_artifact(path))
        if not plan.title.strip() or not plan.rationale.strip():
            return EvaluationResult(False, "plan_missing_title_or_rationale")
        if not changed_paths:
            return EvaluationResult(False, "no_files_changed")
        if not functional_paths:
            return EvaluationResult(False, "proposal_or_log_only_change", {"changed_paths": relative_changed})
        if not diff_paths:
            return EvaluationResult(False, "empty_git_diff", {"changed_paths": relative_changed})
        if not verification.passed:
            return EvaluationResult(False, "verification_failed", {"returncode": verification.returncode})
        return EvaluationResult(
            True,
            "accepted",
            {
                "changed_paths": relative_changed,
                "functional_paths": functional_paths,
                "test_command": " ".join(verification.command),
            },
        )

    @staticmethod
    def _is_artifact(path: str) -> bool:
        return path.startswith(ARTIFACT_PREFIXES)

