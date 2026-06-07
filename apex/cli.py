from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from apex.core.plan_loader import load_plan
from apex.run_cycle import run_manual_cycle


def main() -> int:
    parser = argparse.ArgumentParser(description="Run one APEX V2 manual improvement cycle.")
    parser.add_argument("plan", type=Path, help="Path to a strict JSON change plan.")
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Repository root. Defaults to cwd.")
    parser.add_argument("--no-commit", action="store_true", help="Evaluate and rollback failures, but do not commit accepted changes.")
    args = parser.parse_args()

    plan = load_plan(args.plan)
    result = run_manual_cycle(args.root, plan, commit=not args.no_commit)
    print(json.dumps(asdict(result), indent=2, default=str))
    return 0 if result.accepted else 1


if __name__ == "__main__":
    raise SystemExit(main())

