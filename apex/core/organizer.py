"""Multi-cycle objective decomposer for L5 organizer-level objectives.

Reads an L5 organizer-level objective JSON and emits an ordered,
dependency-tagged list of single-cycle goals consumable by the
existing plan_loader/run_cycle pipeline.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _load_objective(path: str | Path) -> dict[str, Any]:
    """Load and minimally validate an organizer objective JSON file."""
    p = Path(path)
    with p.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"Objective JSON must be an object: {p}")
    objectives = data.get("objectives")
    if not isinstance(objectives, list) or not objectives:
        raise ValueError(
            f"Objective JSON must define a non-empty 'objectives' list: {p}"
        )
    for idx, obj in enumerate(objectives):
        if not isinstance(obj, dict):
            raise ValueError(f"Objective entry #{idx} must be an object")
        if "id" not in obj or "description" not in obj:
            raise ValueError(
                f"Objective entry #{idx} must include 'id' and 'description'"
            )
    return data


def _topological_order(objectives: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return objectives sorted in a stable, deterministic dependency order."""
    by_id = {obj["id"]: obj for obj in objectives}
    for obj in objectives:
        for dep in obj.get("depends_on", []):
            if dep not in by_id:
                raise ValueError(
                    f"Objective {obj['id']} depends on unknown {dep}"
                )
            if dep == obj["id"]:
                raise ValueError(f"Objective {obj['id']} depends on itself")

    visited: set[str] = set()
    visiting: set[str] = set()
    order: list[dict[str, Any]] = []

    def visit(obj_id: str) -> None:
        if obj_id in visited:
            return
        if obj_id in visiting:
            raise ValueError(f"Cycle in objective dependencies: {obj_id}")
        visiting.add(obj_id)
        obj = by_id[obj_id]
        for dep in obj.get("depends_on", []):
            visit(dep)
        visiting.remove(obj_id)
        visited.add(obj_id)
        order.append(obj)

    for obj in objectives:
        visit(obj["id"])
    return order


def decompose_objective(path: str | Path) -> list[dict[str, Any]]:
    """Decompose an organizer objective JSON into ordered, dependency-tagged goals.

    Each emitted goal is a single-cycle goal consumable by the existing
    plan_loader/run_cycle pipeline.
    """
    data = _load_objective(path)
    title = data.get("title", "Organizer objective")
    ordered = _topological_order(data["objectives"])

    goals: list[dict[str, Any]] = []
    for obj in ordered:
        goals.append(
            {
                "id": obj["id"],
                "title": obj.get("title") or f"{title}: {obj['id']}",
                "description": obj["description"],
                "depends_on": list(obj.get("depends_on", [])),
                "kind": obj.get("kind", "code_change"),
            }
        )
    return goals


def build_single_cycle_plan(objective_path: str | Path) -> dict[str, Any]:
    """Build a single-cycle plan dict from an organizer objective JSON.

    The returned dict is shaped to be consumable by apex.core.plan_loader.
    """
    data = _load_objective(objective_path)
    return {
        "title": data.get("title", "Organizer objective"),
        "description": data.get("description", ""),
        "goals": decompose_objective(objective_path),
    }
