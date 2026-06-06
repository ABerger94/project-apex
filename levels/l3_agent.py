from levels.l5_capabilities import capability_signals


def baseline_signals() -> dict[str, float | bool]:
    signals = {
        "planning_quality": 0.52,
        "execution_success": 0.45,
        "verification_coverage": 0.40,
        "rollback_ready": True,
        "novelty_score": 0.25,
        "measured_gain": 0.10,
        "coordination_score": 0.20,
        "accountability_score": 0.30,
    }
    for signal, delta in capability_signals().items():
        if signal in signals and isinstance(signals[signal], float):
            signals[signal] = min(1.0, signals[signal] + delta)
    return signals
