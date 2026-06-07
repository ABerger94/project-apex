from __future__ import annotations

from pathlib import Path

from apex.core.context import read_repo_context
from apex.core.evaluator import Evaluator
from apex.core.git_ops import GitOps
from apex.core.models import ChangePlan, CycleResult
from apex.core.patcher import Patcher
from apex.core.verifier import Verifier


def run_manual_cycle(root: Path, plan: ChangePlan, commit: bool = True) -> CycleResult:
    root = root.resolve()
    read_repo_context(root)
    git = GitOps(root)
    patch_result = Patcher(root).apply(plan)
    verification = Verifier(root).run(plan.verification_command)
    diff_paths = tuple(git.diff_name_only())
    evaluation = Evaluator().evaluate(plan, patch_result.changed_paths, verification, diff_paths, root)

    commit_hash = None
    if evaluation.accepted and commit:
        git.add(list(patch_result.changed_paths))
        commit_hash = git.commit(f"APEX V2 improvement: {plan.title}")
    elif not evaluation.accepted:
        git.rollback_paths(list(patch_result.changed_paths))

    return CycleResult(
        accepted=evaluation.accepted,
        reason=evaluation.reason,
        title=plan.title,
        changed_paths=tuple(str(path.relative_to(root)) for path in patch_result.changed_paths),
        commit_hash=commit_hash,
        verification=verification,
        evaluation=evaluation,
    )

