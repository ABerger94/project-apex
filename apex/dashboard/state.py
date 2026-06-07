from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from apex.core.context import read_repo_context
from apex.core.git_ops import GitOps
from apex.core.memory import EventMemory
from apex.objectives import AGI_LEVELS, TARGET_AGI_LEVEL, TARGET_OBJECTIVE


def dashboard_state(root: Path, event_limit: int = 80) -> dict:
    root = root.resolve()
    context = read_repo_context(root)
    events = [asdict(event) for event in EventMemory(root / "memory" / "events.jsonl").read_recent(event_limit)]
    return {
        "objective": {
            "target_level": TARGET_AGI_LEVEL,
            "target_objective": TARGET_OBJECTIVE,
            "levels": [asdict(level) for level in AGI_LEVELS],
        },
        "repo": {
            "root": str(root),
            "branch": context.branch,
            "status": list(context.status),
            "tracked_file_count": len(context.tracked_files),
            "recent_commits": list(context.recent_commits),
        },
        "events": events,
        "cycles": summarize_cycles(events),
        "generated_from": "memory/events.jsonl",
    }


def summarize_cycles(events: list[dict]) -> list[dict]:
    starts: dict[str, dict] = {}
    cycles: list[dict] = []
    for event in events:
        event_type = event.get("event_type")
        data = event.get("data") or {}
        title = str(data.get("title") or "")
        if event_type == "cycle_started":
            starts[title] = event
        elif event_type == "cycle_finished":
            started = starts.get(title)
            cycles.append({
                "title": title,
                "started_at": started.get("timestamp") if started else None,
                "finished_at": event.get("timestamp"),
                "accepted": bool(data.get("accepted")),
                "reason": data.get("reason"),
                "commit_hash": data.get("commit_hash"),
                "changed_paths": list(data.get("changed_paths") or []),
            })
    return list(reversed(cycles))


def recent_git_commits(root: Path, limit: int = 12) -> list[str]:
    return GitOps(root).recent_commits(limit=limit)

