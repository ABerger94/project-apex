# Project APEX V2

APEX V2 is a clean rebuild focused on trustworthy self-improvement toward Level 5 AGI behavior.

## Mission

The overall goal is for APEX to reach and act as a **Level 5 AGI Organizer**: a system capable of performing the work of entire organizations by managing complex processes, making high-level decisions, and coordinating large-scale operations.

The AGI capability ladder is hardcoded in `apex/objectives.py` and must guide planning, evaluation, and future prompts:

1. **Conversational AI/Chatbots**: AI systems can hold conversations with humans, understand and respond to human language, and support human-like interaction.
2. **Human-Level Problem Solving/Reasoners**: AI systems can solve problems at a human level, evaluate reliability, and reduce hallucinations.
3. **Agents**: AI systems can take actions on behalf of users, perform tasks, make decisions, execute plans autonomously, and verify outcomes.
4. **Innovators**: AI systems can create new innovations, original ideas, inventions, and approaches.
5. **Organizers**: AI systems can perform the work of entire organizations by managing complex processes, making high-level decisions, and coordinating large-scale operations.

The first milestone is intentionally narrow: run one manual improvement cycle that:

1. Reads repository context.
2. Applies one concrete source/test code change.
3. Runs deterministic verification.
4. Evaluates whether the change is meaningful.
5. Commits only if the quality gate passes.
6. Rolls back otherwise.

No scheduler, dashboard, route expansion, or multi-provider orchestration belongs in V2 until the manual cycle is reliable.

The `claude-apex files/` directory is reference material only. Useful ideas may be adapted into V2, but broad shell tools, global rollback, and unrestricted file access are intentionally excluded from the core.

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

## Current Core

- `apex/core/plan_loader.py`: strict JSON plan loading.
- `apex/core/patcher.py`: safe path-resolved file operations.
- `apex/core/executor.py`: allowlisted command execution.
- `apex/core/verifier.py`: syntax checks plus deterministic test command.
- `apex/core/evaluator.py`: rejects proposal/log-only changes.
- `apex/core/memory.py`: append-only structured event log.
- `apex/run_cycle.py`: one manual cycle with scoped commit or rollback.
