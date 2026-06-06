from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone

from config import CONFIG
from core.oracle import create_oracle, LocalOracle
from levels.l3_agent import baseline_signals
from metrics import assess_capabilities, identify_largest_gap
from self_edit.engine import SelfEditEngine


MAX_PROPOSAL_ATTEMPTS = 12
RETRYABLE_REASONS = {"duplicate_proposal", "already_implemented"}


def run_cycle(cycle_number: int) -> dict:
    scores = assess_capabilities(baseline_signals())
    gap = identify_largest_gap(scores)
    oracle = create_oracle(CONFIG.base44)
    editor = SelfEditEngine(CONFIG.root, CONFIG.sandbox)
    rejected: list[dict] = []
    attempts: list[dict] = []
    # Load current objectives and pick the first incomplete one
    objectives = load_objectives()
    active_objective = next((o for o in objectives if not o.get("completed")), None)

    for attempt_number in range(1, MAX_PROPOSAL_ATTEMPTS + 1):
        hypothesis = oracle.propose(scores, gap, rejected)
        result = editor.apply_and_verify(hypothesis)
        attempt = {
            "attempt": attempt_number,
            "hypothesis": hypothesis.__dict__,
            "accepted": result.accepted,
            "commit_hash": result.commit_hash,
            "result_reason": result.reason,
            "proposal_path": str(result.proposal_path.relative_to(CONFIG.root)),
            "changed_paths": [str(path.relative_to(CONFIG.root)) for path in result.changed_paths],
        }
        attempts.append(attempt)
        if result.accepted or result.reason not in RETRYABLE_REASONS:
            break
        rejected.append({
            "title": hypothesis.title,
            "target_signal": hypothesis.target_signal,
            "reason": result.reason,
            "proposal_path": attempt["proposal_path"],
        })

    event = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "cycle": cycle_number,
        "scores": scores.__dict__,
        "current_level": scores.current_level,
        "gap": gap,
        "hypothesis": hypothesis.__dict__,
        "active_objective": active_objective,
        "accepted": result.accepted,
        "commit_hash": result.commit_hash,
        "result_reason": result.reason,
        "proposal_path": str(result.proposal_path.relative_to(CONFIG.root)),
        "changed_paths": [str(path.relative_to(CONFIG.root)) for path in result.changed_paths],
        "attempts": attempts,
    }
    append_memory(event)

    # If the cycle accepted a change, mark the active objective completed and persist
    if result.accepted and active_objective is not None:
        for obj in objectives:
            if obj.get("id") == active_objective.get("id"):
                obj["completed"] = True
        save_objectives(objectives)
    return event


def append_memory(event: dict) -> None:
    CONFIG.memory_log.parent.mkdir(parents=True, exist_ok=True)
    with CONFIG.memory_log.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, sort_keys=True) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the APEX autonomous progressive execution loop.")
    parser.add_argument("--cycles", type=int, default=CONFIG.max_cycles)
    args = parser.parse_args()
    # Ensure objectives exist before running cycles. If none exist, generate 1-3 default objectives and a simple roadmap.
    ensure_objectives()

    for cycle in range(1, args.cycles + 1):
        event = run_cycle(cycle)
        print(json.dumps(event, indent=2, sort_keys=True))
    return 0


def ensure_objectives() -> list[dict]:
    objectives_path = CONFIG.root / "memory" / "objectives.json"
    objectives_path.parent.mkdir(parents=True, exist_ok=True)
    # If file exists and has at least one incomplete objective, return it
    if objectives_path.exists():
        try:
            data = json.loads(objectives_path.read_text(encoding="utf-8"))
            if isinstance(data, list) and any(not o.get("completed") for o in data):
                return data
        except (OSError, json.JSONDecodeError):
            pass

    # Either missing file or all objectives complete: generate new 1-3 objectives
    local_oracle = LocalOracle()
    defaults = local_oracle._default_routes()
    count = min(3, len(defaults))
    objectives: list[dict] = []
    for i in range(count):
        route = defaults[i]
        roadmap = [line.strip() for line in str(route.get("body", "")).splitlines() if line.strip()]
        objectives.append({
            "id": i + 1,
            "title": route.get("title", ""),
            "rationale": route.get("rationale", ""),
            "target_signal": route.get("target_signal", ""),
            "expected_delta": route.get("expected_delta", 0.0),
            "roadmap": roadmap,
            "completed": False,
        })

    objectives_path.write_text(json.dumps(objectives, indent=2), encoding="utf-8")
    return objectives


def load_objectives() -> list[dict]:
    path = CONFIG.root / "memory" / "objectives.json"
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(data, list):
        return []
    return data


def save_objectives(objectives: list[dict]) -> None:
    path = CONFIG.root / "memory" / "objectives.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(objectives, indent=2), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
