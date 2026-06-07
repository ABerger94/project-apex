from __future__ import annotations

import subprocess
from pathlib import Path


class GitOps:
    def __init__(self, root: Path) -> None:
        self.root = root

    def run(self, args: list[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", *args],
            cwd=self.root,
            text=True,
            capture_output=True,
            check=False,
        )

    def current_branch(self) -> str:
        result = self.run(["branch", "--show-current"])
        return result.stdout.strip() or "unknown"

    def status_short(self) -> list[str]:
        return [line for line in self.run(["status", "--short"]).stdout.splitlines() if line]

    def tracked_files(self) -> list[str]:
        return [line for line in self.run(["ls-files"]).stdout.splitlines() if line]

    def recent_commits(self, limit: int = 8) -> list[str]:
        result = self.run(["log", f"-{limit}", "--oneline"])
        return [line for line in result.stdout.splitlines() if line]

    def diff_name_only(self, extra_paths: list[Path] | None = None) -> list[str]:
        result = self.run(["diff", "--name-only"])
        paths = [line for line in result.stdout.splitlines() if line]
        if extra_paths:
            tracked = set(self.tracked_files())
            for path in extra_paths:
                relative = str(path.relative_to(self.root)).replace("\\", "/")
                if relative not in tracked and path.exists():
                    paths.append(relative)
        return list(dict.fromkeys(paths))

    def add(self, paths: list[Path]) -> None:
        if not paths:
            return
        result = self.run(["add", *[str(path.relative_to(self.root)) for path in paths]])
        if result.returncode != 0:
            raise RuntimeError(result.stderr or result.stdout)

    def commit(self, message: str) -> str:
        result = self.run(["commit", "-m", message])
        if result.returncode != 0:
            raise RuntimeError(result.stderr or result.stdout)
        rev = self.run(["rev-parse", "--short", "HEAD"])
        if rev.returncode != 0:
            raise RuntimeError(rev.stderr or rev.stdout)
        return rev.stdout.strip()

    def rollback_paths(self, paths: list[Path]) -> None:
        tracked = set(self.tracked_files())
        tracked_paths = []
        untracked_paths = []
        for path in paths:
            relative = str(path.relative_to(self.root)).replace("\\", "/")
            if relative in tracked:
                tracked_paths.append(relative)
            else:
                untracked_paths.append(path)
        if tracked_paths:
            self.run(["restore", "--", *tracked_paths])
        for path in untracked_paths:
            if path.exists() and path.is_file():
                path.unlink()
