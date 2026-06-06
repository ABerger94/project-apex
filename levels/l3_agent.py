def baseline_signals() -> dict[str, float | bool]:
    return {
        "planning_quality": 0.52,
        "execution_success": 0.45,
        "verification_coverage": 0.40,
        "rollback_ready": True,
        "novelty_score": 0.25,
        "measured_gain": 0.10,
        "coordination_score": 0.20,
        "accountability_score": 0.30,
    }
