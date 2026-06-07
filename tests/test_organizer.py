"""Tests for apex.core.organizer multi-cycle objective decomposer."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from apex.core.organizer import (
    build_single_cycle_plan,
    decompose_objective,
)


EXAMPLE_OBJECTIVE = {
    "title": "Add multi-cycle objective decomposer",
    "description": "Decompose a high-level L5 objective into ordered single-cycle goals.",
    "objectives": [
        {
            "id": "design-organizer-api",
            "title": "Design the organizer decomposer API",
            "description": "Define the function signature and output shape.",
            "depends_on": [],
        },
        {
            "id": "implement-decomposer",
            "title": "Implement the decomposer",
            "description": "Implement deterministic topological ordering.",
            "depends_on": ["design-organizer-api"],
        },
        {
            "id": "add-example-objective",
            "title": "Add an example organizer objective",
            "description": "Provide an example JSON file.",
            "depends_on": ["design-organizer-api"],
        },
        {
            "id": "test-decomposer",
            "title": "Test determinism and dependency ordering",
            "description": "Add tests asserting deterministic output.",
            "depends_on": ["implement-decomposer", "add-example-objective"],
        },
    ],
}


def _write_objective(tmp_dir: Path) -> Path:
    p = tmp_dir / "organizer_objective.json"
    p.write_text(json.dumps(EXAMPLE_OBJECTIVE), encoding="utf-8")
    return p


class OrganizerDecomposerTests(unittest.TestCase):
    def test_decompose_is_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = _write_objective(Path(tmp))
            first = decompose_objective(path)
            second = decompose_objective(path)
            self.assertEqual(first, second)

    def test_dependency_ordering_is_topological(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = _write_objective(Path(tmp))
            goals = decompose_objective(path)
            ids = [g["id"] for g in goals]
            self.assertLess(
                ids.index("design-organizer-api"),
                ids.index("implement-decomposer"),
            )
            self.assertLess(
                ids.index("design-organizer-api"),
                ids.index("add-example-objective"),
            )
            self.assertLess(
                ids.index("implement-decomposer"),
                ids.index("test-decomposer"),
            )
            self.assertLess(
                ids.index("add-example-objective"),
                ids.index("test-decomposer"),
            )

    def test_depends_on_is_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = _write_objective(Path(tmp))
            goals = decompose_objective(path)
            by_id = {g["id"]: g for g in goals}
            self.assertEqual(
                by_id["implement-decomposer"]["depends_on"],
                ["design-organizer-api"],
            )
            self.assertEqual(
                sorted(by_id["test-decomposer"]["depends_on"]),
                ["add-example-objective", "implement-decomposer"],
            )

    def test_build_single_cycle_plan_shape(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = _write_objective(Path(tmp))
            plan = build_single_cycle_plan(path)
            self.assertEqual(plan["title"], EXAMPLE_OBJECTIVE["title"])
            self.assertEqual(
                len(plan["goals"]),
                len(EXAMPLE_OBJECTIVE["objectives"]),
            )

    def test_examples_plan_file_is_valid(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        example = repo_root / "examples" / "plans" / "organizer_objective.json"
        if not example.exists():
            self.skipTest(f"Example objective not present: {example}")
        goals = decompose_objective(example)
        self.assertGreaterEqual(len(goals), 2)
        ids = {g["id"] for g in goals}
        for g in goals:
            for dep in g["depends_on"]:
                self.assertIn(dep, ids)


if __name__ == "__main__":
    unittest.main()
