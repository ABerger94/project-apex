from __future__ import annotations

from pathlib import Path

from apex.core.git_ops import GitOps
from apex.core.models import RepoContext


def read_repo_context(root: Path) -> RepoContext:
    git = GitOps(root)
    return RepoContext(
        root=root,
        branch=git.current_branch(),
        status=tuple(git.status_short()),
        tracked_files=tuple(git.tracked_files()),
        recent_commits=tuple(git.recent_commits(limit=8)),
    )

