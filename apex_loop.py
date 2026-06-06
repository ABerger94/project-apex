from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone

from config import CONFIG
from core.oracle import create_oracle
from levels.l3_agent import baseline_signals
from metrics import assess_capabilities, identify_largest_gap
from self_edit.engine import SelfEditEngine


def run_cycle(cycle_number: int) -> dict:
    scores = assess_capabilities(baseline_signals())
    gap = identify_largest_gap(scores)
    oracle = create_oracle(CONFIG.base44)
    hypothesis = oracle.propose(scores, gap)
    editor = SelfEditEngine(CONFIG.root, CONFIG.sandbox)
    result = editor.apply_and_verify(hypothesis)

    event = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "cycle": cycle_number,
        "scores": scores.__dict__,
        "current_level": scores.current_level,
        "gap": gap,
        "hypothesis": hypothesis.__dict__,
        "accepted": result.accepted,
        "commit_hash": result.commit_hash,
        "proposal_path": str(result.proposal_path.relative_to(CONFIG.root)),
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
