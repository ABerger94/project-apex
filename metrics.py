from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CapabilityScores:
    l3_agent: float
    l4_innovator: float
    l5_organizer: float

    @property
    def aggregate(self) -> float:
        return round((self.l3_agent * 0.45) + (self.l4_innovator * 0.30) + (self.l5_organizer * 0.25), 4)

    @property
    def current_level(self) -> str:
        if self.l5_organizer >= 0.90:
            return "L5"
        if self.l4_innovator >= 0.80:
            return "L4"
        if self.l3_agent >= 0.70:
            return "L3"
        return "L2"


def clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def assess_capabilities(signals: dict[str, float | bool | int]) -> CapabilityScores:
    planning = float(signals.get("planning_quality", 0.45))
    execution = float(signals.get("execution_success", 0.40))
    verification = float(signals.get("verification_coverage", 0.35))
    rollback = 1.0 if signals.get("rollback_ready", False) else 0.0
    novelty = float(signals.get("novelty_score", 0.20))
    measured_gain = float(signals.get("measured_gain", 0.10))
    coordination = float(signals.get("coordination_score", 0.15))
    accountability = float(signals.get("accountability_score", 0.25))

    l3 = (planning * 0.30) + (execution * 0.35) + (verification * 0.25) + (rollback * 0.10)
    l4 = (l3 * 0.35) + (novelty * 0.35) + (measured_gain * 0.30)
    l5 = (l4 * 0.30) + (coordination * 0.40) + (accountability * 0.30)

    return CapabilityScores(clamp(l3), clamp(l4), clamp(l5))


def identify_largest_gap(scores: CapabilityScores) -> str:
    gaps = {
        "L3 execution reliability": 0.70 - scores.l3_agent,
        "L4 validated innovation": 0.80 - scores.l4_innovator,
        "L5 organizational coordination": 0.90 - scores.l5_organizer,
    }
    return max(gaps, key=gaps.get)
