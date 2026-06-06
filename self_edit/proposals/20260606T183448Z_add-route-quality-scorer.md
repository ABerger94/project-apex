# Add route quality scorer

Rationale: APEX planning quality improves when the oracle favors routes whose signals have not yet been saturated.
Target signal: planning_quality
Expected delta: 0.06

```text
# Proposal: add route quality scorer
Score each proposal route by historical acceptance rate for its target signal.
De-prioritize signals that have already accumulated high deltas to promote balanced capability growth.
Primary gap: L5 organizational coordination

```
