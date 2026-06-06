from __future__ import annotations


CAPABILITIES = [{'evidence': 'Implemented by SelfEditEngine from accepted hypothesis.',
  'expected_delta': 0.09,
  'id': 'add-executive-decision-ledger',
  'implemented_at': '2026-06-06T11:08:53.637536+00:00',
  'rationale': 'Organization-scale AI must make and audit high-level decisions across complex '
               'processes.',
  'target_signal': 'accountability_score',
  'title': 'Add executive decision ledger'}]


def capability_signals() -> dict[str, float]:
    signals: dict[str, float] = {}
    for capability in CAPABILITIES:
        signal = str(capability.get("target_signal", ""))
        if not signal:
            continue
        delta = float(capability.get("expected_delta", 0.0))
        signals[signal] = min(1.0, signals.get(signal, 0.0) + max(0.0, delta))
    return signals
