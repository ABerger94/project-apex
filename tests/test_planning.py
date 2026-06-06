import tempfile
import unittest
from pathlib import Path

from core.planning import Objective, PlanTask, PlanningEngine, Roadmap
from metrics import CapabilityScores


_SCORES_LOW = CapabilityScores(0.4, 0.2, 0.1)
_SIGNALS = {
    "planning_quality": 0.52,
    "execution_success": 0.45,
    "verification_coverage": 0.40,
    "rollback_ready": True,
    "novelty_score": 0.25,
    "measured_gain": 0.10,
    "coordination_score": 0.20,
    "accountability_score": 0.30,
}


def _engine(tmp: str) -> PlanningEngine:
    return PlanningEngine(
        objectives_path=Path(tmp) / "objectives.json",
        roadmap_path=Path(tmp) / "roadmap.json",
    )


class ObjectiveGenerationTests(unittest.TestCase):
    def test_generates_one_to_three_objectives(self):
        with tempfile.TemporaryDirectory() as tmp:
            engine = _engine(tmp)
            objectives = engine.generate_objectives(_SCORES_LOW, "L5 organizational coordination", _SIGNALS)
            self.assertGreaterEqual(len(objectives), 1)
            self.assertLessEqual(len(objectives), 3)

    def test_primary_objective_targets_l5_coordination_gap(self):
        with tempfile.TemporaryDirectory() as tmp:
            objectives = _engine(tmp).generate_objectives(
                _SCORES_LOW, "L5 organizational coordination", _SIGNALS
            )
            self.assertEqual(objectives[0].target_signal, "coordination_score")

    def test_primary_objective_targets_l4_novelty_gap(self):
        with tempfile.TemporaryDirectory() as tmp:
            objectives = _engine(tmp).generate_objectives(
                _SCORES_LOW, "L4 validated innovation", _SIGNALS
            )
            self.assertEqual(objectives[0].target_signal, "novelty_score")

    def test_primary_objective_targets_l3_execution_gap(self):
        scores = CapabilityScores(0.3, 0.1, 0.05)
        with tempfile.TemporaryDirectory() as tmp:
            objectives = _engine(tmp).generate_objectives(scores, "L3 execution reliability", _SIGNALS)
            self.assertEqual(objectives[0].target_signal, "execution_success")

    def test_each_objective_has_required_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            objectives = _engine(tmp).generate_objectives(
                _SCORES_LOW, "L5 organizational coordination", _SIGNALS
            )
            for obj in objectives:
                self.assertTrue(obj.id, "id must be non-empty")
                self.assertTrue(obj.description, "description must be non-empty")
                self.assertTrue(obj.target_signal, "target_signal must be non-empty")
                self.assertTrue(obj.success_criteria, "success_criteria must be non-empty")
                self.assertGreater(obj.target_score, obj.current_score)

    def test_objectives_start_as_active(self):
        with tempfile.TemporaryDirectory() as tmp:
            objectives = _engine(tmp).generate_objectives(
                _SCORES_LOW, "L5 organizational coordination", _SIGNALS
            )
            for obj in objectives:
                self.assertEqual(obj.status, "active")

    def test_secondary_l5_objective_is_accountability(self):
        with tempfile.TemporaryDirectory() as tmp:
            objectives = _engine(tmp).generate_objectives(
                _SCORES_LOW, "L5 organizational coordination", _SIGNALS
            )
            signals = [o.target_signal for o in objectives]
            self.assertIn("accountability_score", signals)

    def test_load_returns_empty_when_no_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = _engine(tmp).load_objectives()
            self.assertEqual(result, [])

    def test_objectives_roundtrip_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            engine = _engine(tmp)
            objectives = engine.generate_objectives(
                _SCORES_LOW, "L5 organizational coordination", _SIGNALS
            )
            engine.save_objectives(objectives)
            loaded = engine.load_objectives()
            self.assertEqual(len(loaded), len(objectives))
            self.assertEqual(loaded[0].target_signal, objectives[0].target_signal)
            self.assertEqual(loaded[0].id, objectives[0].id)

    def test_only_active_objectives_influence_next_cycle(self):
        with tempfile.TemporaryDirectory() as tmp:
            engine = _engine(tmp)
            objectives = engine.generate_objectives(
                _SCORES_LOW, "L5 organizational coordination", _SIGNALS
            )
            objectives[0].status = "achieved"
            engine.save_objectives(objectives)
            loaded = engine.load_objectives()
            active = [o for o in loaded if o.status == "active"]
            self.assertLess(len(active), len(objectives))


class RoadmapBuildTests(unittest.TestCase):
    def test_roadmap_has_tasks(self):
        with tempfile.TemporaryDirectory() as tmp:
            engine = _engine(tmp)
            objectives = engine.generate_objectives(
                _SCORES_LOW, "L5 organizational coordination", _SIGNALS
            )
            roadmap = engine.build_roadmap(objectives, cycle=1)
            self.assertTrue(roadmap.tasks)

    def test_each_task_has_owner_gate_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            engine = _engine(tmp)
            objectives = engine.generate_objectives(
                _SCORES_LOW, "L5 organizational coordination", _SIGNALS
            )
            roadmap = engine.build_roadmap(objectives, cycle=1)
            for task in roadmap.tasks:
                self.assertTrue(task.owner, f"Task {task.id} missing owner")
                self.assertTrue(task.gate_condition, f"Task {task.id} missing gate_condition")
                self.assertTrue(task.verification_evidence, f"Task {task.id} missing verification_evidence")

    def test_each_objective_gets_three_tasks(self):
        with tempfile.TemporaryDirectory() as tmp:
            engine = _engine(tmp)
            objectives = engine.generate_objectives(
                _SCORES_LOW, "L5 organizational coordination", _SIGNALS
            )
            roadmap = engine.build_roadmap(objectives, cycle=1)
            for obj in objectives:
                obj_tasks = [t for t in roadmap.tasks if t.objective_id == obj.id]
                self.assertEqual(len(obj_tasks), 3, f"Objective {obj.id} should have 3 tasks")

    def test_task_dependency_chain_assess_propose_verify(self):
        with tempfile.TemporaryDirectory() as tmp:
            engine = _engine(tmp)
            objectives = engine.generate_objectives(
                _SCORES_LOW, "L5 organizational coordination", _SIGNALS
            )[:1]
            roadmap = engine.build_roadmap(objectives, cycle=1)
            obj = objectives[0]
            assess = next(t for t in roadmap.tasks if t.id == f"{obj.id}-assess")
            propose = next(t for t in roadmap.tasks if t.id == f"{obj.id}-propose")
            verify = next(t for t in roadmap.tasks if t.id == f"{obj.id}-verify")
            self.assertEqual(assess.depends_on, [])
            self.assertEqual(propose.depends_on, [assess.id])
            self.assertEqual(verify.depends_on, [propose.id])

    def test_assess_task_owner_is_metrics(self):
        with tempfile.TemporaryDirectory() as tmp:
            engine = _engine(tmp)
            objectives = engine.generate_objectives(
                _SCORES_LOW, "L5 organizational coordination", _SIGNALS
            )[:1]
            roadmap = engine.build_roadmap(objectives, cycle=1)
            obj = objectives[0]
            assess = next(t for t in roadmap.tasks if t.id == f"{obj.id}-assess")
            self.assertEqual(assess.owner, "metrics")

    def test_roadmap_roundtrip_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            engine = _engine(tmp)
            objectives = engine.generate_objectives(
                _SCORES_LOW, "L5 organizational coordination", _SIGNALS
            )
            roadmap = engine.build_roadmap(objectives, cycle=3)
            engine.save_roadmap(roadmap)
            loaded = engine.load_roadmap()
            self.assertIsNotNone(loaded)
            self.assertEqual(loaded.cycle, 3)
            self.assertEqual(loaded.id, roadmap.id)
            self.assertEqual(len(loaded.tasks), len(roadmap.tasks))

    def test_load_roadmap_returns_none_when_no_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = _engine(tmp).load_roadmap()
            self.assertIsNone(result)

    def test_roadmap_tasks_start_as_pending(self):
        with tempfile.TemporaryDirectory() as tmp:
            engine = _engine(tmp)
            objectives = engine.generate_objectives(
                _SCORES_LOW, "L5 organizational coordination", _SIGNALS
            )
            roadmap = engine.build_roadmap(objectives, cycle=1)
            for task in roadmap.tasks:
                self.assertEqual(task.status, "pending")


if __name__ == "__main__":
    unittest.main()
