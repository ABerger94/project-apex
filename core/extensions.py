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
