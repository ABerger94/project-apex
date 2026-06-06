from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from config import ROOT
from metrics import CapabilityScores

OBJECTIVES_PATH = ROOT / "memory" / "objectives.json"
ROADMAP_PATH = ROOT / "memory" / "roadmap.json"

_SIGNAL_OWNER = {
    "planning_quality": "oracle",
    "execution_success": "engine",
    "verification_coverage": "engine",
    "rollback_ready": "engine",
    "novelty_score": "oracle",
    "measured_gain": "metrics",
    "coordination_score": "loop",
    "accountability_score": "loop",
}

_SIGNAL_TARGETS = {
    "planning_quality": 0.70,
    "execution_success": 0.70,
    "verification_coverage": 0.65,
    "rollback_ready": 1.0,
    "novelty_score": 0.60,
    "measured_gain": 0.50,
    "coordination_score": 0.60,
    "accountability_score": 0.60,
}


@dataclass
class Objective:
    id: str
    description: str
    target_signal: str
    current_score: float
    target_score: float
    success_criteria: str
    deadline_cycles: int = 3
    status: str = "active"


@dataclass
class PlanTask:
    id: str
    title: str
    owner: str
    objective_id: str
    depends_on: list
    gate_condition: str
    verification_evidence: str
    status: str = "pending"


@dataclass
class Roadmap:
    id: str
    cycle: int
    created_at: str
    objectives: list
    tasks: list
    status: str = "active"

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> Roadmap:
        objectives = [Objective(**o) for o in data.get("objectives", [])]
        tasks = [PlanTask(**t) for t in data.get("tasks", [])]
        return cls(
            id=data["id"],
            cycle=data["cycle"],
            created_at=data["created_at"],
            objectives=objectives,
            tasks=tasks,
            status=data.get("status", "active"),
        )


class PlanningEngine:
    def __init__(
        self,
        objectives_path: Path = OBJECTIVES_PATH,
        roadmap_path: Path = ROADMAP_PATH,
    ) -> None:
        self.objectives_path = objectives_path
        self.roadmap_path = roadmap_path

    def load_objectives(self) -> list:
        if not self.objectives_path.exists():
            return []
        try:
            data = json.loads(self.objectives_path.read_text(encoding="utf-8"))
            return [Objective(**item) for item in data if isinstance(item, dict)]
        except (OSError, json.JSONDecodeError, TypeError):
            return []

    def save_objectives(self, objectives: list) -> None:
        self.objectives_path.parent.mkdir(parents=True, exist_ok=True)
        self.objectives_path.write_text(
            json.dumps([asdict(o) for o in objectives], indent=2),
            encoding="utf-8",
        )

    def generate_objectives(
        self,
        scores: CapabilityScores,
        gap: str,
        signals: Optional[dict] = None,
    ) -> list:
        objectives = []
        signals = signals or {}

        primary_signal = _gap_to_primary_signal(gap)
        current = float(signals.get(primary_signal, _score_for_signal(scores, primary_signal)))
        target = _SIGNAL_TARGETS.get(primary_signal, 0.70)
        objectives.append(Objective(
            id=_short_id(),
            description=f"Improve {primary_signal} to close the {gap}",
            target_signal=primary_signal,
            current_score=round(current, 4),
            target_score=target,
            success_criteria=(
                f"{primary_signal} >= {target} after proposal implementation, "
                "verified by re-running assess_capabilities()"
            ),
            deadline_cycles=3,
        ))

        secondary_signal = _secondary_signal(gap, primary_signal)
        if secondary_signal:
            current2 = float(signals.get(secondary_signal, _score_for_signal(scores, secondary_signal)))
            target2 = _SIGNAL_TARGETS.get(secondary_signal, 0.60)
            if current2 < target2:
                objectives.append(Objective(
                    id=_short_id(),
                    description=f"Raise {secondary_signal} to reinforce {gap} progress",
                    target_signal=secondary_signal,
                    current_score=round(current2, 4),
                    target_score=target2,
                    success_criteria=f"{secondary_signal} >= {target2} in episodic_log signal snapshot",
                    deadline_cycles=5,
                ))

        if scores.l3_agent < 0.70 and primary_signal != "execution_success":
            current3 = float(signals.get("execution_success", scores.l3_agent))
            target3 = _SIGNAL_TARGETS["execution_success"]
            if current3 < target3:
                objectives.append(Objective(
                    id=_short_id(),
                    description="Stabilize L3 execution_success as foundation for higher capability levels",
                    target_signal="execution_success",
                    current_score=round(current3, 4),
                    target_score=target3,
                    success_criteria=(
                        f"execution_success >= {target3} with zero test rollbacks in the cycle"
                    ),
                    deadline_cycles=2,
                ))

        return objectives[:3]

    def build_roadmap(self, objectives: list, cycle: int) -> Roadmap:
        tasks = []
        for obj in objectives:
            tasks.extend(self._tasks_for_objective(obj))
        return Roadmap(
            id=_short_id(),
            cycle=cycle,
            created_at=datetime.now(timezone.utc).isoformat(),
            objectives=objectives,
            tasks=tasks,
        )

    def save_roadmap(self, roadmap: Roadmap) -> None:
        self.roadmap_path.parent.mkdir(parents=True, exist_ok=True)
        self.roadmap_path.write_text(
            json.dumps(roadmap.to_dict(), indent=2),
            encoding="utf-8",
        )

    def load_roadmap(self) -> Optional[Roadmap]:
        if not self.roadmap_path.exists():
            return None
        try:
            data = json.loads(self.roadmap_path.read_text(encoding="utf-8"))
            return Roadmap.from_dict(data)
        except (OSError, json.JSONDecodeError, KeyError):
            return None

    def _tasks_for_objective(self, obj: Objective) -> list:
        owner = _SIGNAL_OWNER.get(obj.target_signal, "loop")
        assess_id = f"{obj.id}-assess"
        propose_id = f"{obj.id}-propose"
        verify_id = f"{obj.id}-verify"
        gap_delta = round(obj.target_score - obj.current_score, 4)

        return [
            PlanTask(
                id=assess_id,
                title=f"Assess current {obj.target_signal} baseline",
                owner="metrics",
                objective_id=obj.id,
                depends_on=[],
                gate_condition="assess_capabilities(baseline_signals()) returns CapabilityScores",
                verification_evidence=(
                    f"{obj.target_signal} current value ({obj.current_score}) "
                    "recorded in episodic_log scores snapshot"
                ),
            ),
            PlanTask(
                id=propose_id,
                title=f"Propose and apply change targeting {obj.target_signal}",
                owner=owner,
                objective_id=obj.id,
                depends_on=[assess_id],
                gate_condition=(
                    f"no existing capability covers {obj.target_signal} "
                    f"with accumulated delta >= {gap_delta}"
                ),
                verification_evidence=(
                    "hypothesis accepted by SelfEditEngine: "
                    "tests pass, commit_hash non-null, proposal written to self_edit/proposals/"
                ),
            ),
            PlanTask(
                id=verify_id,
                title=f"Verify {obj.target_signal} progress toward {obj.target_score}",
                owner="metrics",
                objective_id=obj.id,
                depends_on=[propose_id],
                gate_condition="result.accepted is True and result.commit_hash is not None",
                verification_evidence=(
                    f"reassessed {obj.target_signal} shows monotone improvement; "
                    f"target {obj.target_score} logged in next cycle's episodic_log"
                ),
            ),
        ]


def _short_id() -> str:
    return str(uuid.uuid4())[:8]


def _gap_to_primary_signal(gap: str) -> str:
    if "L5" in gap:
        return "coordination_score"
    if "L4" in gap:
        return "novelty_score"
    return "execution_success"


def _secondary_signal(gap: str, primary: str) -> Optional[str]:
    if "L5" in gap and primary != "accountability_score":
        return "accountability_score"
    if "L4" in gap and primary != "measured_gain":
        return "measured_gain"
    if "L3" in gap and primary != "planning_quality":
        return "planning_quality"
    return None


def _score_for_signal(scores: CapabilityScores, signal: str) -> float:
    l5 = {"coordination_score", "accountability_score"}
    l4 = {"novelty_score", "measured_gain"}
    if signal in l5:
        return scores.l5_organizer
    if signal in l4:
        return scores.l4_innovator
    return scores.l3_agent
