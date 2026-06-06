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
    def propose(self, scores: CapabilityScores, gap: str) -> Hypothesis:
        raise NotImplementedError


class LocalOracle(Oracle):
    def propose(self, scores: CapabilityScores, gap: str) -> Hypothesis:
        patch = (
            "# Proposal: improve benchmark observability\n"
            "Add richer benchmark signals before attempting autonomous code mutation.\n"
            f"Current aggregate score: {scores.aggregate}\n"
            f"Primary gap: {gap}\n"
        )
        return Hypothesis(
            title="Increase benchmark observability",
            rationale="APEX should improve measurement before trusting self-edits.",
            target_signal="verification_coverage",
            expected_delta=0.05,
            proposed_patch=patch,
        )


class Base44Oracle(Oracle):
    def __init__(self, config: Base44Config) -> None:
        self.config = config

    def propose(self, scores: CapabilityScores, gap: str) -> Hypothesis:
        if not self.config.enabled:
            return LocalOracle().propose(scores, gap)

        prompt = {
            "role": "APEX Oracle",
            "task": "Propose one small reversible code change to improve APEX capability.",
            "scores": scores.__dict__,
            "gap": gap,
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
            fallback = LocalOracle().propose(scores, gap)
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
