"""Capability self-assessment against the L1-L5 AGI ladder.

This module lets the APEX system evaluate its own current capabilities
and identify gaps to the next level. It is a small, reversible step
toward L4 Innovator (self-reflection) and L5 Organizer (evidence-based
high-level decision making).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class LevelCriterion:
    name: str
    description: str


LEVELS: Dict[int, LevelCriterion] = {
    1: LevelCriterion(
        name="Conversational AI",
        description="Hold conversations, understand and respond to language.",
    ),
    2: LevelCriterion(
        name="Human-Level Reasoning",
        description="Solve problems at human level with reliable evaluation.",
    ),
    3: LevelCriterion(
        name="Agent",
        description=(
            "Take actions, perform tasks, execute plans autonomously, "
            "and verify outcomes."
        ),
    ),
    4: LevelCriterion(
        name="Innovator",
        description=(
            "Generate original ideas, inventions, and approaches that "
            "push beyond routine problem solving."
        ),
    ),
    5: LevelCriterion(
        name="Organizer",
        description=(
            "Manage complex processes, make high-level decisions, and "
            "coordinate large-scale operations with evidence and "
            "accountability."
        ),
    ),
}


_REQUIRED_FEATURES: Dict[int, List[str]] = {
    1: ["conversational"],
    2: ["conversational", "reasoning"],
    3: ["conversational", "reasoning", "action", "verification"],
    4: [
        "conversational",
        "reasoning",
        "action",
        "verification",
        "reflection",
    ],
    5: [
        "conversational",
        "reasoning",
        "action",
        "verification",
        "reflection",
        "coordination",
    ],
}


def current_level(features: Dict[str, bool]) -> int:
    """Return the highest level whose required features are all present."""
    achieved = 0
    for level in sorted(_REQUIRED_FEATURES.keys()):
        required = _REQUIRED_FEATURES[level]
        if all(bool(features.get(key, False)) for key in required):
            achieved = level
        else:
            break
    return achieved


def gaps_to_next(features: Dict[str, bool]) -> List[str]:
    """Return the missing feature names required to reach the next level."""
    achieved = current_level(features)
    next_level = achieved + 1
    if next_level not in _REQUIRED_FEATURES:
        return []
    needed = _REQUIRED_FEATURES[next_level]
    return [name for name in needed if not bool(features.get(name, False))]


def describe() -> Dict[int, str]:
    """Return a mapping of level number to human-readable description."""
    return {level: crit.description for level, crit in LEVELS.items()}
