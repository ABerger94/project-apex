from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone

from config import CONFIG
from core.oracle import create_oracle
from levels.l3_agent import baseline_signals
from metrics import assess_capabilities, identify_largest_gap
from self_edit.engine import SelfEditEngine


MAX_PROPOSAL_ATTEMPTS = 12


def run_cycle(cycle_number: int) -> dict:
    scores = assess_capabilities(baseline_signals())
    gap = identify_largest_gap(scores)
    oracle = create_oracle(CONFIG.base44)
    editor = SelfEditEngine(CONFIG.root, CONFIG.sandbox)
    rejected: list[dict] = []
    attempts: list[dict] = []

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
        }
        attempts.append(attempt)
        if result.accepted or result.reason != "duplicate_proposal":
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
        "accepted": result.accepted,
        "commit_hash": result.commit_hash,
        "result_reason": result.reason,
        "proposal_path": str(result.proposal_path.relative_to(CONFIG.root)),
        "attempts": attempts,
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
