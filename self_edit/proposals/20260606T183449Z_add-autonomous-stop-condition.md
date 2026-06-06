# Add autonomous stop condition

Rationale: Continuous autonomy should stop when cycles fail to make accepted progress, then explain what blocked progress.
Target signal: execution_success
Expected delta: 0.05

```text
# Proposal: add autonomous stop condition
If a scheduler-triggered cycle has no accepted change, stop the scheduler and record the blocking reason.
Require a different hypothesis source or user review before resuming continuous mode.
Primary gap: L5 organizational coordination

```
