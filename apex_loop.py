from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Optional

from config import CONFIG
from core.oracle import create_oracle
from core.planning import PlanningEngine
from core.repair import classify_failure, choose_repair
from levels.l3_agent import baseline_signals
from metrics import assess_capabilities, identify_largest_gap
from self_edit.engine import SelfEditEngine


MAX_PROPOSAL_ATTEMPTS = 12
RETRYABLE_REASONS = {"duplicate_proposal", "already_implemented", "tests_failed"}


def run_cycle(cycle_number: int) -> dict:
    signals = baseline_signals()
    scores = assess_capabilities(signals)
    gap = identify_largest_gap(scores)
    oracle = create_oracle(CONFIG.base44)
    editor = SelfEditEngine(CONFIG.root, CONFIG.sandbox)
    planner = PlanningEngine()

    objectives = [o for o in planner.load_objectives() if o.status == "active"]
    if not objectives:
        objectives = planner.generate_objectives(scores, gap, signals)
        planner.save_objectives(objectives)

    roadmap = planner.build_roadmap(objectives, cycle_number)
    planner.save_roadmap(roadmap)

    rejected: list[dict] = []
    attempts: list[dict] = []
    tried_signals: set[str] = set()
    current_gap = gap
    preferred_signal: Optional[str] = None

    for attempt_number in range(1, MAX_PROPOSAL_ATTEMPTS + 1):
        hypothesis = oracle.propose(scores, current_gap, rejected, preferred_signal)
        tried_signals.add(hypothesis.target_signal)
        result = editor.apply_and_verify(hypothesis)
        attempt: dict = {
            "attempt": attempt_number,
            "hypothesis": hypothesis.__dict__,
            "accepted": result.accepted,
            "commit_hash": result.commit_hash,
            "result_reason": result.reason,
            "proposal_path": str(result.proposal_path.relative_to(CONFIG.root)),
            "changed_paths": [str(p.relative_to(CONFIG.root)) for p in result.changed_paths],
        }

        if result.accepted or result.reason not in RETRYABLE_REASONS:
            attempts.append(attempt)
            break

        failure_class = classify_failure(result.reason)
        repair = choose_repair(failure_class, hypothesis.target_signal, current_gap, tried_signals)
        attempt["repair"] = {"strategy": repair.strategy, "rationale": repair.rationale}
        attempts.append(attempt)

        preferred_signal = repair.new_target_signal
        if repair.new_gap_override:
            current_gap = repair.new_gap_override

        rejected.append({
            "title": hypothesis.title,
            "target_signal": hypothesis.target_signal,
            "reason": result.reason,
            "repair_strategy": repair.strategy,
            "proposal_path": attempt["proposal_path"],
        })

    if result.accepted:
        for obj in objectives:
            if obj.target_signal == hypothesis.target_signal:
                obj.status = "achieved"
        planner.save_objectives(objectives)

    event = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "cycle": cycle_number,
        "scores": scores.__dict__,
        "current_level": scores.current_level,
        "gap": gap,
        "hypothesis": hypothesis.__dict__,
        "accepted": result.accepted,
        "commit_hash": result.commit_hash,
        "result_reason": result.reason,
        "proposal_path": str(result.proposal_path.relative_to(CONFIG.root)),
        "changed_paths": [str(p.relative_to(CONFIG.root)) for p in result.changed_paths],
        "attempts": attempts,
        "objectives": [asdict(o) for o in objectives],
        "roadmap_id": roadmap.id,
    }
    append_memory(event)
    return event


def append_memory(event: dict) -> None:
    CONFIG.memory_log.parent.mkdir(parents=True, exist_ok=True)
    with CONFIG.memory_log.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, sort_keys=True) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the APEX autonomous progressive execution loop.")
    parser.add_argument("--cycles", type=int, default=CONFIG.max_cycles)
    args = parser.parse_args()

    for cycle in range(1, args.cycles + 1):
        event = run_cycle(cycle)
        print(json.dumps(event, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
