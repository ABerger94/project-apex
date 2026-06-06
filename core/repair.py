from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class FailureClass(Enum):
    DUPLICATE = "duplicate_proposal"
    CAPABILITY_EXISTS = "already_implemented"
    TEST_FAILURE = "tests_failed"
    COMMIT_FAILURE = "commit_failed"
    UNKNOWN = "unknown"


@dataclass
class RepairAction:
    strategy: str
    rationale: str
    new_target_signal: Optional[str] = None
    new_gap_override: Optional[str] = None
    decompose_hint: Optional[str] = None


_ALL_SIGNALS = [
    "coordination_score",
    "accountability_score",
    "measured_gain",
    "novelty_score",
    "planning_quality",
    "execution_success",
    "verification_coverage",
]

_GAP_SEQUENCE = [
    "L5 organizational coordination",
    "L4 validated innovation",
    "L3 execution reliability",
]

_L5_SIGNALS = {"coordination_score", "accountability_score"}
_L4_SIGNALS = {"novelty_score", "measured_gain"}


def classify_failure(reason: str) -> FailureClass:
    return {
        "duplicate_proposal": FailureClass.DUPLICATE,
        "already_implemented": FailureClass.CAPABILITY_EXISTS,
        "tests_failed": FailureClass.TEST_FAILURE,
        "patch_failed": FailureClass.TEST_FAILURE,   # treat like test failure: decompose to simpler scope
        "commit_failed": FailureClass.COMMIT_FAILURE,
    }.get(reason, FailureClass.UNKNOWN)


def choose_repair(
    failure_class: FailureClass,
    current_signal: str,
    current_gap: str,
    tried_signals: set[str],
) -> RepairAction:
    if failure_class == FailureClass.DUPLICATE:
        next_sig = _next_untried(tried_signals, current_signal)
        return RepairAction(
            strategy="shift_signal",
            rationale=(
                "Proposal is an exact duplicate of a prior submission; "
                "shifting to a different capability signal to avoid the same route."
            ),
            new_target_signal=next_sig,
        )

    if failure_class == FailureClass.CAPABILITY_EXISTS:
        next_gap = _next_gap(current_gap)
        return RepairAction(
            strategy="advance_gap",
            rationale=(
                "Capability is already implemented; the current gap is covered. "
                "Advancing to the next unresolved gap."
            ),
            new_gap_override=next_gap,
        )

    if failure_class == FailureClass.TEST_FAILURE:
        simpler = _simpler_signal(current_signal)
        return RepairAction(
            strategy="decompose",
            rationale=(
                "Tests failed after applying the proposal; decomposing to a simpler, "
                "lower-scope signal to reduce implementation risk."
            ),
            new_target_signal=simpler,
            decompose_hint="Target one function or data structure, not a full module.",
        )

    if failure_class == FailureClass.COMMIT_FAILURE:
        alternate = _next_untried(tried_signals, current_signal)
        return RepairAction(
            strategy="alternate_signal",
            rationale=(
                "Git commit failed due to environment state; "
                "switching to an alternate signal to avoid repeating the same patch."
            ),
            new_target_signal=alternate,
        )

    return RepairAction(
        strategy="simplify",
        rationale="Unclassified failure; attempting a simpler, lower-delta proposal.",
        new_target_signal=_next_untried(tried_signals, current_signal),
    )


def _next_untried(tried: set[str], current: str) -> str:
    for sig in _ALL_SIGNALS:
        if sig not in tried and sig != current:
            return sig
    for sig in _ALL_SIGNALS:
        if sig != current:
            return sig
    return _ALL_SIGNALS[0]


def _next_gap(current_gap: str) -> str:
    for i, gap in enumerate(_GAP_SEQUENCE):
        if gap == current_gap and i + 1 < len(_GAP_SEQUENCE):
            return _GAP_SEQUENCE[i + 1]
    return _GAP_SEQUENCE[-1]


def _simpler_signal(current_signal: str) -> str:
    if current_signal in _L5_SIGNALS:
        return "measured_gain"
    if current_signal in _L4_SIGNALS:
        return "execution_success"
    return "verification_coverage"
