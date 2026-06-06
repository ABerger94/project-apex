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
  'title': 'Add multi-workstream orchestration map'},
 {'evidence': 'Implemented by SelfEditEngine from accepted hypothesis.',
  'expected_delta': 0.1,
  'id': 'add-sub-agent-team-operating-model',
  'implemented_at': '2026-06-06T17:30:54.933419+00:00',
  'rationale': 'L5 organizers need to coordinate teams of specialized sub-agents with delegated '
               'responsibilities and escalation paths.',
  'target_signal': 'coordination_score',
  'title': 'Add sub-agent team operating model'},
 {'evidence': "Code patch applied to ['core/extensions.py']; tests passed; committed.",
  'expected_delta': 0.06,
  'id': 'add-novel-signal-detector',
  'implemented_at': '2026-06-06T18:34:34.335118+00:00',
  'rationale': 'Novelty improves when APEX can identify which signals have been over-targeted and '
               'pivot to under-served ones.',
  'target_signal': 'novelty_score',
  'title': 'Add novel signal detector'},
 {'evidence': "Code patch applied to ['core/extensions.py']; tests passed; committed.",
  'expected_delta': 0.06,
  'id': 'add-route-quality-scorer',
  'implemented_at': '2026-06-06T18:34:48.881608+00:00',
  'rationale': 'APEX planning quality improves when the oracle favors routes whose signals have '
               'not yet been saturated.',
  'target_signal': 'planning_quality',
  'title': 'Add route quality scorer'},
 {'evidence': "Code patch applied to ['core/extensions.py']; tests passed; committed.",
  'expected_delta': 0.05,
  'id': 'add-autonomous-stop-condition',
  'implemented_at': '2026-06-06T18:34:49.158580+00:00',
  'rationale': 'Continuous autonomy should stop when cycles fail to make accepted progress, then '
               'explain what blocked progress.',
  'target_signal': 'execution_success',
  'title': 'Add autonomous stop condition'},
 {'evidence': "Code patch applied to ['core/extensions.py']; tests passed; committed.",
  'expected_delta': 0.07,
  'id': 'add-accountability-signal-audit',
  'implemented_at': '2026-06-06T18:34:49.444670+00:00',
  'rationale': 'L5 requires organization-level accountability, not just individual task execution.',
  'target_signal': 'accountability_score',
  'title': 'Add accountability signal audit'},
 {'evidence': "Code patch applied to ['core/extensions.py']; tests passed; committed.",
  'expected_delta': 0.07,
  'id': 'add-l5-dependency-map',
  'implemented_at': '2026-06-06T18:34:49.785262+00:00',
  'rationale': 'L5 behavior needs explicit dependency tracking across workstreams before it can '
               'coordinate organization-scale execution.',
  'target_signal': 'coordination_score',
  'title': 'Add L5 dependency map'},
 {'evidence': "Code patch applied to ['core/extensions.py']; tests passed; committed.",
  'expected_delta': 0.08,
  'id': 'add-process-portfolio-coordinator',
  'implemented_at': '2026-06-06T18:34:50.036462+00:00',
  'rationale': 'An L5 organizer must coordinate a portfolio of processes, not just isolated tasks.',
  'target_signal': 'measured_gain',
  'title': 'Add process portfolio coordinator'}]


def capability_signals() -> dict[str, float]:
    signals: dict[str, float] = {}
    for capability in CAPABILITIES:
        signal = str(capability.get("target_signal", ""))
        if not signal:
            continue
        delta = float(capability.get("expected_delta", 0.0))
        signals[signal] = min(1.0, signals.get(signal, 0.0) + max(0.0, delta))
    return signals
