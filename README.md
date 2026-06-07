# Project APEX V2

APEX V2 is a clean rebuild focused on trustworthy self-improvement.

The first milestone is intentionally narrow: run one manual improvement cycle that:

1. Reads repository context.
2. Applies one concrete source/test code change.
3. Runs deterministic verification.
4. Evaluates whether the change is meaningful.
5. Commits only if the quality gate passes.
6. Rolls back otherwise.

No scheduler, dashboard, route expansion, or multi-provider orchestration belongs in V2 until the manual cycle is reliable.

## Manual Cycle Contract

A valid self-improvement cycle must:

- change at least one functional source or test file;
- avoid proposal-only, memory-only, or log-only changes;
- pass the configured test command;
- produce a non-empty git diff before commit;
- record a structured cycle result.

## Run Tests

```powershell
python -m unittest discover -s tests
```

