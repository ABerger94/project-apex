# Project APEX

Autonomous Progressive Execution system: a small, testable scaffold for iterative agent capability growth.

## Current shape

- `config.py` defines levels, benchmark weights, sandbox policy, and Base44 environment variables.
- `metrics.py` scores Level 3 agent execution, Level 4 innovation, and Level 5 organization capability.
- `apex_loop.py` runs one or more assess-plan-edit-test-log cycles.
- `core/oracle.py` provides the reasoning interface with a local fallback and an optional Base44 `InvokeLLM` path.
- `self_edit/engine.py` writes proposed changes in a sandbox branch, runs tests, commits on pass, and rolls back on fail.
- `memory/episodic_log.jsonl` stores cycle history.

## Environment

Create `.env` from `.env.example` and fill in Base44 values:

```powershell
BASE44_APP_ID=your_base44_app_id
VITE_BASE44_APP_ID=your_base44_app_id
BASE44_APP_BASE_URL=https://your-app.base44.app
VITE_BASE44_APP_BASE_URL=https://your-app.base44.app
```

`BASE44_APP_ID` is used first. `VITE_BASE44_APP_ID` exists for compatibility with Vite/Base44 apps.

## Run

```powershell
python -m unittest discover -s tests
python apex_loop.py --cycles 1
```

Base44 LLM calls are disabled unless `APEX_ORACLE_PROVIDER=base44` is set.
Run `npm install` first if you want the Base44 Oracle adapter to call `base44.integrations.Core.InvokeLLM`.

## Command Center

Start the local dashboard:

```powershell
npm run dashboard
```

Open `http://localhost:4177` to view runs, proposals, Git commits, working tree status, and to launch a one-cycle APEX run.
The dashboard also includes an autonomous scheduler for interval runs, such as every 1, 2, or 5 hours, plus a continuous mode that starts the next cycle as soon as the prior cycle finishes.
The APEX Chat panel can answer questions from current logs, commits, proposals, scheduler state, and source summaries. Set `APEX_CHAT_PROVIDER=groq` and `GROQ_API_KEY` to route chat answers through Groq. Set `APEX_CHAT_PROVIDER=base44` with Base44 env vars to route chat answers through `InvokeLLM`; otherwise it uses a local grounded responder.

Windows launchers are available in `scripts/`:

```powershell
scripts\apex-dashboard.cmd
scripts\apex-cycle.cmd
```
