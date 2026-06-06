from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass

from config import Base44Config
from metrics import CapabilityScores


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
    def propose(self, scores: CapabilityScores, gap: str, rejected: list[dict] | None = None) -> Hypothesis:
        rejected_titles = {str(item.get("title", "")).lower() for item in rejected or []}
        options = [
            Hypothesis(
                title="Increase benchmark observability",
                rationale="APEX should improve measurement before trusting self-edits.",
                target_signal="verification_coverage",
                expected_delta=0.05,
                proposed_patch=(
                    "# Proposal: improve benchmark observability\n"
                    "Add richer benchmark signals before attempting autonomous code mutation.\n"
                    f"Current aggregate score: {scores.aggregate}\n"
                    f"Primary gap: {gap}\n"
                ),
            ),
            Hypothesis(
                title="Add L5 coordination benchmark",
                rationale="The largest gap is organizational coordination, so APEX needs a benchmark that measures delegated workflows.",
                target_signal="coordination_score",
                expected_delta=0.08,
                proposed_patch=(
                    "# Proposal: add L5 coordination benchmark\n"
                    "Define a repeatable scenario where APEX plans owners, dependencies, status checks, and completion evidence.\n"
                    "Score whether each dependency has an accountable owner and measurable completion criteria.\n"
                    f"Primary gap: {gap}\n"
                ),
            ),
            Hypothesis(
                title="Add accountability signal audit",
                rationale="L5 requires organization-level accountability, not just individual task execution.",
                target_signal="accountability_score",
                expected_delta=0.07,
                proposed_patch=(
                    "# Proposal: add accountability signal audit\n"
                    "Record whether every APEX action has a responsible module, expected outcome, verification method, and rollback path.\n"
                    "Use the audit to penalize vague proposals and reward operationally complete plans.\n"
                    f"Primary gap: {gap}\n"
                ),
            ),
            Hypothesis(
                title="Add anti-stagnation proposal policy",
                rationale="APEX cannot progress toward L5 if it repeats proposals after rejection.",
                target_signal="measured_gain",
                expected_delta=0.06,
                proposed_patch=(
                    "# Proposal: add anti-stagnation proposal policy\n"
                    "When a hypothesis is rejected as duplicate, require the next hypothesis to target a different signal or a different L5 capability.\n"
                    "Track rejected titles and patches in the cycle log so future cycles can avoid them.\n"
                    f"Primary gap: {gap}\n"
                ),
            ),
        ]
        for option in options:
            if option.title.lower() not in rejected_titles:
                return option
        return options[-1]


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
