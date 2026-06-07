from __future__ import annotations

import shutil
from pathlib import Path

from apex.core.executor import AllowlistedExecutor
from apex.core.git_ops import GitOps
from apex.core.models import ChangePlan, PreflightResult
from apex.core.patcher import Patcher


def run_preflight(root: Path, plan: ChangePlan) -> PreflightResult:
    root = root.resolve()
    git = GitOps(root)
    if not git.is_repository():
        return PreflightResult(False, "not_a_git_repository", {"root": str(root)})

    try:
        planned_paths = tuple(str(path.relative_to(root)).replace("\\", "/") for path in Patcher(root).planned_paths(plan))
    except ValueError as error:
        return PreflightResult(False, "unsafe_plan_path", {"error": str(error)})

    dirty_paths = git.dirty_paths()
    conflicts = tuple(path for path in planned_paths if path in dirty_paths)
    if conflicts:
        return PreflightResult(
            False,
            "dirty_plan_paths",
            {
                "planned_paths": planned_paths,
                "dirty_paths": tuple(sorted(dirty_paths)),
                "conflicts": conflicts,
            },
        )

    if not plan.verification_command:
        return PreflightResult(False, "empty_verification_command")
    executable = plan.verification_command[0]
    if Path(executable).is_absolute():
        executable_found = Path(executable).exists()
    else:
        executable_found = shutil.which(executable) is not None
    if not executable_found:
        return PreflightResult(False, "verification_executable_not_found", {"executable": executable})

    try:
        AllowlistedExecutor(root)._validate(plan.verification_command)
    except ValueError as error:
        return PreflightResult(False, "verification_command_not_allowlisted", {"error": str(error)})

    return PreflightResult(
        True,
        "passed",
        {
            "planned_paths": planned_paths,
            "dirty_path_count": len(dirty_paths),
            "verification_command": tuple(plan.verification_command),
        },
    )
