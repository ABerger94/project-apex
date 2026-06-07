from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from apex.core.planner import OllamaPlanner, plan_to_json
from apex.core.plan_loader import load_plan
from apex.run_cycle import run_dry_cycle, run_manual_cycle


def main() -> int:
    parser = argparse.ArgumentParser(description="Run or prepare one APEX V2 manual improvement cycle.")
    parser.add_argument("plan", type=Path, nargs="?", help="Path to a strict JSON change plan.")
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Repository root. Defaults to cwd.")
    parser.add_argument("--no-commit", action="store_true", help="Evaluate and rollback failures, but do not commit accepted changes.")
    parser.add_argument("--dry-run", action="store_true", help="Run the cycle in a temporary repository copy without mutating the root.")
    parser.add_argument("--generate-plan", metavar="GOAL", help="Ask the configured Ollama model for a strict JSON plan.")
    parser.add_argument("--output", type=Path, help="Write a generated plan to this path instead of stdout.")
    args = parser.parse_args()

    if args.generate_plan:
        plan = OllamaPlanner().propose(args.root, args.generate_plan)
        plan_json = plan_to_json(plan)
        if args.output:
            args.output.write_text(plan_json + "\n", encoding="utf-8")
        else:
            print(plan_json)
        return 0

    if args.plan is None:
        parser.error("a plan path is required unless --generate-plan is used")

    plan = load_plan(args.plan)
    result = run_dry_cycle(args.root, plan) if args.dry_run else run_manual_cycle(args.root, plan, commit=not args.no_commit)
    print(json.dumps(asdict(result), indent=2, default=str))
    return 0 if result.accepted else 1


if __name__ == "__main__":
    raise SystemExit(main())
