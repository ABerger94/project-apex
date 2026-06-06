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
