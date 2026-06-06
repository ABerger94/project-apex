from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

from config import Base44Config, ROOT
from metrics import CapabilityScores


DEFAULT_ROUTE_PATH = ROOT / "memory" / "proposal_routes.json"
L5_SIGNALS = {"coordination_score", "accountability_score", "measured_gain"}
L5_KEYWORDS = (
    "l5",
    "organization",
    "sub-agent",
    "subagent",
    "team",
    "workflow",
    "dependency",
    "executive",
    "decision",
    "large-scale",
    "coordination",
    "accountability",
)


@dataclass(frozen=True)
class Hypothesis:
    title: str
    rationale: str
    target_signal: str
    expected_delta: float
    proposed_patch: str


class Oracle:
    def propose(self, scores: CapabilityScores, gap: str, rejected: list[dict] | None = None) -> Hypothesis:
        raise NotImplementedError


class LocalOracle(Oracle):
    def __init__(self, route_path: Path = DEFAULT_ROUTE_PATH) -> None:
        self.route_path = route_path

    def propose(self, scores: CapabilityScores, gap: str, rejected: list[dict] | None = None) -> Hypothesis:
        rejected_titles = {str(item.get("title", "")).lower() for item in rejected or []}
        routes = self._rank_routes(self._load_routes(), gap)
        for route in routes:
            if route["title"].lower() not in rejected_titles:
                return self._route_to_hypothesis(route, scores, gap)

        route = self._expand_routes(routes, scores, gap)
        return self._route_to_hypothesis(route, scores, gap)

    def _load_routes(self) -> list[dict]:
        self.route_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.route_path.exists():
            routes = self._default_routes()
            self._save_routes(routes)
            return routes

        try:
            routes = json.loads(self.route_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            routes = []

        if not isinstance(routes, list):
            routes = []

        seen = {str(route.get("title", "")).lower() for route in routes if isinstance(route, dict)}
        for route in self._default_routes():
            if route["title"].lower() not in seen:
                routes.append(route)
        self._save_routes(routes)
        return routes

    def _save_routes(self, routes: list[dict]) -> None:
        self.route_path.parent.mkdir(parents=True, exist_ok=True)
        self.route_path.write_text(json.dumps(routes, indent=2), encoding="utf-8")

    def _expand_routes(self, routes: list[dict], scores: CapabilityScores, gap: str) -> dict:
        route_number = len(routes) + 1
        signal_cycle = ["coordination_score", "accountability_score", "measured_gain"]
        target_signal = signal_cycle[route_number % len(signal_cycle)]
        theme_cycle = [
            "sub-agent operating model",
            "multi-workstream dependency control",
            "executive decision ledger",
            "large-scale process coordinator",
            "cross-functional accountability board",
        ]
        theme = theme_cycle[route_number % len(theme_cycle)]
        route = {
            "title": f"Explore L5 route {route_number}: {theme}",
            "rationale": "The known proposal routes were rejected or exhausted, so APEX is expanding route memory with a new organization-scale L5 path.",
            "target_signal": target_signal,
            "expected_delta": 0.08,
            "body": (
                f"# Proposal: expand L5 route memory with {theme}\n"
                f"Create route {route_number} for {target_signal} using {theme}.\n"
                "Define sub-agent roles, delegated workflow steps, decision authority, evidence gates, and rollback criteria.\n"
                "Require the next implementation to improve organization-scale coordination or accountability.\n"
                f"Current aggregate score: {scores.aggregate}\n"
                f"Primary gap: {gap}\n"
            ),
            "source": "local_oracle_expansion",
        }
        routes.append(route)
        self._save_routes(routes)
        return route

    def _rank_routes(self, routes: list[dict], gap: str) -> list[dict]:
        return sorted(routes, key=lambda route: self._route_priority(route, gap), reverse=True)

    def _route_priority(self, route: dict, gap: str) -> tuple[int, int, float]:
        text = " ".join(str(route.get(key, "")) for key in ("title", "rationale", "body")).lower()
        l5_signal = 1 if str(route.get("target_signal", "")) in L5_SIGNALS else 0
        keyword_hits = sum(1 for keyword in L5_KEYWORDS if keyword in text)
        gap_bonus = 1 if "l5" in gap.lower() and l5_signal else 0
        return (l5_signal + gap_bonus, keyword_hits, float(route.get("expected_delta", 0.0)))

    def _route_to_hypothesis(self, route: dict, scores: CapabilityScores, gap: str) -> Hypothesis:
        return Hypothesis(
            title=str(route["title"]),
            rationale=str(route["rationale"]),
            target_signal=str(route["target_signal"]),
            expected_delta=float(route["expected_delta"]),
            proposed_patch=str(route["body"])
                .replace("{aggregate}", str(scores.aggregate))
                .replace("{gap}", gap),
        )

    @staticmethod
    def _default_routes() -> list[dict]:
        return [
            {
                "title": "Add L5 coordination benchmark",
                "rationale": "The largest gap is organizational coordination, so APEX needs a benchmark that measures delegated workflows.",
                "target_signal": "coordination_score",
                "expected_delta": 0.08,
                "body": "# Proposal: add L5 coordination benchmark\nDefine a repeatable scenario where APEX plans owners, dependencies, status checks, and completion evidence.\nScore whether each dependency has an accountable owner and measurable completion criteria.\nPrimary gap: {gap}\n",
                "source": "default",
            },
            {
                "title": "Add sub-agent team operating model",
                "rationale": "L5 organizers need to coordinate teams of specialized sub-agents with delegated responsibilities and escalation paths.",
                "target_signal": "coordination_score",
                "expected_delta": 0.1,
                "body": "# Proposal: add sub-agent team operating model\nDefine sub-agent roles for planner, executor, verifier, reviewer, and coordinator.\nRoute work through delegated responsibilities, escalation rules, and completion evidence.\nPrimary gap: {gap}\n",
                "source": "default_l5",
            },
            {
                "title": "Add executive decision ledger",
                "rationale": "Organization-scale AI must make and audit high-level decisions across complex processes.",
                "target_signal": "accountability_score",
                "expected_delta": 0.09,
                "body": "# Proposal: add executive decision ledger\nRecord high-level decisions, decision owner, alternatives considered, expected impact, risk, and verification evidence.\nUse the ledger to coordinate large-scale operations and review accountability.\nPrimary gap: {gap}\n",
                "source": "default_l5",
            },
            {
                "title": "Add multi-workstream orchestration map",
                "rationale": "L5 requires managing several workstreams at once, including dependencies, owners, blockers, and delivery gates.",
                "target_signal": "coordination_score",
                "expected_delta": 0.1,
                "body": "# Proposal: add multi-workstream orchestration map\nTrack workstreams, sub-agent owners, dependencies, blockers, status, and next decisions.\nPrioritize actions that unblock the most organization-level work.\nPrimary gap: {gap}\n",
                "source": "default_l5",
            },
            {
                "title": "Add process portfolio coordinator",
                "rationale": "An L5 organizer must coordinate a portfolio of processes, not just isolated tasks.",
                "target_signal": "measured_gain",
                "expected_delta": 0.08,
                "body": "# Proposal: add process portfolio coordinator\nGroup objectives into a portfolio of operational processes with priority, owner, health, and expected outcome.\nSelect next actions based on portfolio-level risk and value.\nPrimary gap: {gap}\n",
                "source": "default_l5",
            },
            {
                "title": "Add accountability signal audit",
                "rationale": "L5 requires organization-level accountability, not just individual task execution.",
                "target_signal": "accountability_score",
                "expected_delta": 0.07,
                "body": "# Proposal: add accountability signal audit\nRecord whether every APEX action has a responsible module, expected outcome, verification method, and rollback path.\nUse the audit to penalize vague proposals and reward operationally complete plans.\nPrimary gap: {gap}\n",
                "source": "default",
            },
            {
                "title": "Add anti-stagnation proposal policy",
                "rationale": "APEX cannot progress toward L5 if it repeats proposals after rejection.",
                "target_signal": "measured_gain",
                "expected_delta": 0.06,
                "body": "# Proposal: add anti-stagnation proposal policy\nWhen a hypothesis is rejected as duplicate, require the next hypothesis to target a different signal or a different L5 capability.\nTrack rejected titles and patches in the cycle log so future cycles can avoid them.\nPrimary gap: {gap}\n",
                "source": "default",
            },
            {
                "title": "Add L5 dependency map",
                "rationale": "L5 behavior needs explicit dependency tracking across workstreams before it can coordinate organization-scale execution.",
                "target_signal": "coordination_score",
                "expected_delta": 0.07,
                "body": "# Proposal: add L5 dependency map\nRepresent each objective as workstreams, dependencies, owners, blockers, and verification gates.\nUse the map to choose next actions that unblock the most downstream work.\nPrimary gap: {gap}\n",
                "source": "default",
            },
            {
                "title": "Add organization-level run review",
                "rationale": "APEX needs to evaluate whether a cycle improved organizational execution rather than only producing an artifact.",
                "target_signal": "accountability_score",
                "expected_delta": 0.06,
                "body": "# Proposal: add organization-level run review\nAfter each cycle, summarize objective, action, evidence, unresolved blockers, and next owner.\nReject cycles that cannot identify measurable organizational progress.\nPrimary gap: {gap}\n",
                "source": "default",
            },
            {
                "title": "Add cross-cycle goal memory",
                "rationale": "Progress toward L5 requires remembering active objectives across cycles instead of evaluating each cycle in isolation.",
                "target_signal": "coordination_score",
                "expected_delta": 0.08,
                "body": "# Proposal: add cross-cycle goal memory\nPersist active L5 objectives, current blockers, last action, and next planned action in memory.\nUse this memory to avoid restarting from the same local benchmark each cycle.\nPrimary gap: {gap}\n",
                "source": "default",
            },
            {
                "title": "Add proposal impact rubric",
                "rationale": "APEX needs a stronger way to rank proposals by expected progress toward L5 coordination and accountability.",
                "target_signal": "measured_gain",
                "expected_delta": 0.06,
                "body": "# Proposal: add proposal impact rubric\nScore each hypothesis on L5 relevance, reversibility, measurable impact, and dependency reduction.\nPrefer proposals that improve coordination or accountability over generic observability work.\nPrimary gap: {gap}\n",
                "source": "default",
            },
            {
                "title": "Add autonomous stop condition",
                "rationale": "Continuous autonomy should stop when cycles fail to make accepted progress, then explain what blocked progress.",
                "target_signal": "execution_success",
                "expected_delta": 0.05,
                "body": "# Proposal: add autonomous stop condition\nIf a scheduler-triggered cycle has no accepted change, stop the scheduler and record the blocking reason.\nRequire a different hypothesis source or user review before resuming continuous mode.\nPrimary gap: {gap}\n",
                "source": "default",
            },
        ]


class Base44Oracle(Oracle):
    def __init__(self, config: Base44Config) -> None:
        self.config = config

    def propose(self, scores: CapabilityScores, gap: str, rejected: list[dict] | None = None) -> Hypothesis:
        if not self.config.enabled:
            return LocalOracle().propose(scores, gap, rejected)

        prompt = {
            "role": "APEX Oracle",
            "task": "Propose one small reversible code change to improve APEX capability. Do not repeat rejected proposals.",
            "scores": scores.__dict__,
            "gap": gap,
            "rejected": rejected or [],
            "schema": {
                "title": "string",
                "rationale": "string",
                "target_signal": "string",
                "expected_delta": "number",
                "proposed_patch": "string",
            },
        }

        script = (
            "const { createClient } = require('@base44/sdk');"
            "const input = JSON.parse(process.argv[1]);"
            "const client = createClient({ appId: process.env.BASE44_APP_ID || process.env.VITE_BASE44_APP_ID, token: process.env.BASE44_ACCESS_TOKEN, serverUrl: '', requiresAuth: false });"
            "client.integrations.Core.InvokeLLM({ prompt: JSON.stringify(input), response_json_schema: input.schema })"
            ".then(r => console.log(JSON.stringify(r)))"
            ".catch(e => { console.error(e.message || String(e)); process.exit(2); });"
        )

        result = subprocess.run(
            ["node", "-e", script, json.dumps(prompt)],
            text=True,
            capture_output=True,
            timeout=45,
            check=False,
        )
        if result.returncode != 0:
            fallback = LocalOracle().propose(scores, gap, rejected)
            return Hypothesis(
                title=fallback.title,
                rationale=f"{fallback.rationale} Base44 InvokeLLM failed: {result.stderr.strip()}",
                target_signal=fallback.target_signal,
                expected_delta=fallback.expected_delta,
                proposed_patch=fallback.proposed_patch,
            )

        data = json.loads(result.stdout)
        return Hypothesis(
            title=str(data.get("title", "Base44 proposal")),
            rationale=str(data.get("rationale", "")),
            target_signal=str(data.get("target_signal", "verification_coverage")),
            expected_delta=float(data.get("expected_delta", 0.0)),
            proposed_patch=str(data.get("proposed_patch", "")),
        )


def create_oracle(config: Base44Config) -> Oracle:
    if config.provider == "base44":
        return Base44Oracle(config)
    return LocalOracle()
