from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from apex.core.context import read_repo_context
from apex.core.evaluator import Evaluator
from apex.core.git_ops import GitOps
from apex.core.memory import EventMemory
from apex.core.models import ChangePlan, CycleResult, EvaluationResult, VerificationResult
from apex.core.patcher import Patcher
from apex.core.preflight import run_preflight
from apex.core.verifier import Verifier


def run_manual_cycle(root: Path, plan: ChangePlan, commit: bool = True, memory_path: Path | None = None) -> CycleResult:
    root = root.resolve()
    memory = EventMemory(memory_path or root / "memory" / "events.jsonl")
    context = read_repo_context(root)
    memory.append("cycle_started", {
        "title": plan.title,
        "branch": context.branch,
        "status_count": len(context.status),
        "target": plan.target,
        "operation_count": len(plan.operations),
        "operations": [
            {
                "kind": operation.kind,
                "path": operation.path,
            }
            for operation in plan.operations
        ],
        "verification_command": list(plan.verification_command),
    })
    git = GitOps(root)
    preflight = run_preflight(root, plan)
    memory.append("cycle_preflight_finished", {
        "title": plan.title,
        "passed": preflight.passed,
        "reason": preflight.reason,
        "evidence": preflight.evidence,
    })
    if not preflight.passed:
        verification = VerificationResult(
            command=plan.verification_command,
            returncode=-1,
            stdout="",
            stderr="",
            passed=False,
            checks=({"name": "preflight", "passed": False, "detail": preflight.reason},),
        )
        evaluation = EvaluationResult(False, preflight.reason, {"preflight": preflight.evidence})
        result = CycleResult(
            accepted=False,
            reason=preflight.reason,
            title=plan.title,
            changed_paths=(),
            commit_hash=None,
            verification=verification,
            evaluation=evaluation,
            preflight=preflight,
            diff_summary=(),
        )
        memory.append("cycle_finished", cycle_finished_payload(result))
        return result

    patch_result = Patcher(root).apply(plan)
    verification = Verifier(root).run(plan.verification_command, patch_result.changed_paths)
    diff_paths = tuple(git.diff_name_only(list(patch_result.changed_paths)))
    diff_summary = tuple(git.diff_stat(list(patch_result.changed_paths)))
    evaluation = Evaluator().evaluate(plan, patch_result.changed_paths, verification, diff_paths, root)

    commit_hash = None
    if evaluation.accepted and commit:
        git.add(list(patch_result.changed_paths))
        commit_hash = git.commit(f"APEX V2 improvement: {plan.title}")
    elif not evaluation.accepted:
        git.rollback_paths(list(patch_result.changed_paths))

    result = CycleResult(
        accepted=evaluation.accepted,
        reason=evaluation.reason,
        title=plan.title,
        changed_paths=tuple(str(path.relative_to(root)) for path in patch_result.changed_paths),
        commit_hash=commit_hash,
        verification=verification,
        evaluation=evaluation,
        preflight=preflight,
        diff_summary=diff_summary,
    )
    memory.append("cycle_finished", cycle_finished_payload(result))
    return result


def run_dry_cycle(root: Path, plan: ChangePlan) -> CycleResult:
    root = root.resolve()
    with tempfile.TemporaryDirectory(prefix="apex-dry-run-") as temp_dir:
        dry_root = Path(temp_dir) / "repo"
        shutil.copytree(root, dry_root, ignore=shutil.ignore_patterns("memory"))
        return run_manual_cycle(dry_root, plan, commit=False, memory_path=dry_root / "memory" / "events.jsonl")


def cycle_finished_payload(result: CycleResult) -> dict:
    return {
        "title": result.title,
        "accepted": result.accepted,
        "reason": result.reason,
        "commit_hash": result.commit_hash,
        "changed_paths": list(result.changed_paths),
        "preflight": {
            "passed": result.preflight.passed,
            "reason": result.preflight.reason,
            "evidence": result.preflight.evidence,
        },
        "diff_summary": list(result.diff_summary),
        "evaluation_evidence": result.evaluation.evidence,
        "verification": {
            "passed": result.verification.passed,
            "returncode": result.verification.returncode,
            "command": list(result.verification.command),
            "checks": result.verification.checks,
            "stdout_tail": tail_text(result.verification.stdout),
            "stderr_tail": tail_text(result.verification.stderr),
        },
    }


def tail_text(value: str, max_chars: int = 2400) -> str:
    value = value or ""
    if len(value) <= max_chars:
        return value
    return value[-max_chars:]
