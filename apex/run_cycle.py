from __future__ import annotations

from pathlib import Path

from apex.core.context import read_repo_context
from apex.core.evaluator import Evaluator
from apex.core.git_ops import GitOps
from apex.core.memory import EventMemory
from apex.core.models import ChangePlan, CycleResult
from apex.core.patcher import Patcher
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
    patch_result = Patcher(root).apply(plan)
    verification = Verifier(root).run(plan.verification_command, patch_result.changed_paths)
    diff_paths = tuple(git.diff_name_only(list(patch_result.changed_paths)))
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
    )
    memory.append("cycle_finished", {
        "title": result.title,
        "accepted": result.accepted,
        "reason": result.reason,
        "commit_hash": result.commit_hash,
        "changed_paths": list(result.changed_paths),
        "evaluation_evidence": result.evaluation.evidence,
        "verification": {
            "passed": result.verification.passed,
            "returncode": result.verification.returncode,
            "command": list(result.verification.command),
            "checks": result.verification.checks,
            "stdout_tail": tail_text(result.verification.stdout),
            "stderr_tail": tail_text(result.verification.stderr),
        },
    })
    return result


def tail_text(value: str, max_chars: int = 2400) -> str:
    value = value or ""
    if len(value) <= max_chars:
        return value
    return value[-max_chars:]
