from __future__ import annotations


CAPABILITIES = [{'evidence': 'Implemented by SelfEditEngine from accepted hypothesis.',
  'expected_delta': 0.09,
  'id': 'add-executive-decision-ledger',
  'implemented_at': '2026-06-06T17:30:53.995025+00:00',
  'rationale': 'Organization-scale AI must make and audit high-level decisions across complex '
               'processes.',
  'target_signal': 'accountability_score',
  'title': 'Add executive decision ledger'},
 {'evidence': 'Implemented by SelfEditEngine from accepted hypothesis.',
  'expected_delta': 0.08,
  'id': 'add-l5-coordination-benchmark',
  'implemented_at': '2026-06-06T17:30:54.259413+00:00',
  'rationale': 'The largest gap is organizational coordination, so APEX needs a benchmark that '
               'measures delegated workflows.',
  'target_signal': 'coordination_score',
  'title': 'Add L5 coordination benchmark'},
 {'evidence': 'Implemented by SelfEditEngine from accepted hypothesis.',
  'expected_delta': 0.06,
  'id': 'add-proposal-impact-rubric',
  'implemented_at': '2026-06-06T17:30:54.499206+00:00',
  'rationale': 'APEX needs a stronger way to rank proposals by expected progress toward L5 '
               'coordination and accountability.',
  'target_signal': 'measured_gain',
  'title': 'Add proposal impact rubric'},
 {'evidence': 'Implemented by SelfEditEngine from accepted hypothesis.',
  'expected_delta': 0.1,
  'id': 'add-multi-workstream-orchestration-map',
  'implemented_at': '2026-06-06T17:30:54.715569+00:00',
  'rationale': 'L5 requires managing several workstreams at once, including dependencies, owners, '
               'blockers, and delivery gates.',
  'target_signal': 'coordination_score',
  'title': 'Add multi-workstream orchestration map'}]


def capability_signals() -> dict[str, float]:
    signals: dict[str, float] = {}
    for capability in CAPABILITIES:
        signal = str(capability.get("target_signal", ""))
        if not signal:
            continue
        delta = float(capability.get("expected_delta", 0.0))
        signals[signal] = min(1.0, signals.get(signal, 0.0) + max(0.0, delta))
    return signals
