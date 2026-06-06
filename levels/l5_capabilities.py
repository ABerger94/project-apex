from __future__ import annotations


CAPABILITIES = []


def capability_signals() -> dict[str, float]:
    signals: dict[str, float] = {}
    for capability in CAPABILITIES:
        signal = str(capability.get("target_signal", ""))
        if not signal:
            continue
        delta = float(capability.get("expected_delta", 0.0))
        signals[signal] = min(1.0, signals.get(signal, 0.0) + max(0.0, delta))
    return signals
