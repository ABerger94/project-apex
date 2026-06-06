from __future__ import annotations

# Extension functions are appended here as APEX proposals are accepted.
# apex_loop.py reloads this module each cycle and calls any available functions.


def detect_novel_signals(events, threshold=3):
    from collections import Counter
    counts = Counter(
        ev.get('hypothesis', {}).get('target_signal', '')
        for ev in events if ev.get('accepted')
    )
    return [sig for sig, n in counts.items() if n >= threshold]


def score_route_by_history(route, accepted_signals):
    signal = str(route.get('target_signal', ''))
    successes = accepted_signals.count(signal)
    if successes == 0:
        return 1.0
    if successes <= 2:
        return 0.7
    return 0.4


def validate_patch_safety(code):
    risky = ['os.system(', 'subprocess.call(', 'eval(', 'exec(', 'shutil.rmtree', '__import__(']
    found = [p for p in risky if p in code]
    if len(code.strip()) < 10:
        found.append('patch_too_short')
    return found


def signal_saturation(capabilities, cap=0.80):
    totals = {}
    for c in capabilities:
        sig = str(c.get('target_signal', ''))
        delta = float(c.get('expected_delta', 0.0))
        totals[sig] = totals.get(sig, 0.0) + delta
    return {sig for sig, total in totals.items() if total >= cap}


def rank_objectives_by_impact(objectives):
    return sorted(
        objectives,
        key=lambda o: o.get('target_score', 0) - o.get('current_score', 0),
        reverse=True,
    )


def verify_gain(before, after):
    keys = ('l3_agent', 'l4_innovator', 'l5_organizer')
    d = lambda k: round(after.get(k, 0) - before.get(k, 0), 4)
    return {
        'l3_delta': d('l3_agent'),
        'l4_delta': d('l4_innovator'),
        'l5_delta': d('l5_organizer'),
        'improved': sum(after.get(k, 0) for k in keys) > sum(before.get(k, 0) for k in keys),
    }


def gap_velocity(events):
    from collections import defaultdict
    totals, counts = defaultdict(float), defaultdict(int)
    for ev in events:
        if ev.get('accepted'):
            gap = ev.get('gap', 'unknown')
            delta = float(ev.get('hypothesis', {}).get('expected_delta', 0.0))
            totals[gap] += delta
            counts[gap] += 1
    return {g: round(totals[g] / counts[g], 4) for g in totals}


def detect_stagnation(events, window=5):
    recent = events[-window:]
    accepted = [e for e in recent if e.get('accepted')]
    signals_used = [e.get('hypothesis', {}).get('target_signal', '') for e in accepted]
    return {
        'window': window,
        'acceptance_rate': round(len(accepted) / max(len(recent), 1), 4),
        'repeated_signals': len(signals_used) != len(set(signals_used)),
        'stagnating': len(accepted) < window // 2,
    }


def audit_cycle(event):
    attempts = event.get('attempts', [])
    strategies = list({
        a.get('repair', {}).get('strategy', '')
        for a in attempts
        if not a.get('accepted') and a.get('repair')
    } - {''})
    return {
        'cycle': event.get('cycle'),
        'gap_addressed': event.get('gap'),
        'proposals_tried': len(attempts),
        'accepted': event.get('accepted'),
        'repair_strategies_used': strategies,
        'accepted_signal': event.get('hypothesis', {}).get('target_signal'),
        'commit': event.get('commit_hash'),
    }
