# Add anti-stagnation proposal policy

Rationale: APEX cannot progress toward L5 if it repeats proposals after rejection.
Target signal: measured_gain
Expected delta: 0.06

```text
# Proposal: add anti-stagnation proposal policy
When a hypothesis is rejected as duplicate, require the next hypothesis to target a different signal or a different L5 capability.
Track rejected titles and patches in the cycle log so future cycles can avoid them.
Primary gap: L3 execution reliability

```
