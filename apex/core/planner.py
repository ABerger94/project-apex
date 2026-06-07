from __future__ import annotations

import json
import os
import urllib.request
from dataclasses import asdict
from pathlib import Path
from typing import Protocol

from apex.core.context import read_repo_context
from apex.core.models import ChangePlan, RepoContext
from apex.core.plan_loader import plan_from_dict


class PlannerTransport(Protocol):
    def generate(self, endpoint: str, payload: dict, headers: dict[str, str], timeout_seconds: int) -> dict:
        ...


class UrlLibTransport:
    def generate(self, endpoint: str, payload: dict, headers: dict[str, str], timeout_seconds: int) -> dict:
        request = urllib.request.Request(
            endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            return json.loads(response.read().decode("utf-8"))


class OllamaPlanner:
    def __init__(
        self,
        model: str | None = None,
        endpoint: str | None = None,
        api_key: str | None = None,
        timeout_seconds: int = 120,
        transport: PlannerTransport | None = None,
    ) -> None:
        self.model = model or os.getenv("OLLAMA_MODEL", "minimax-m3")
        self.api_key = api_key if api_key is not None else os.getenv("OLLAMA_API_KEY")
        self.endpoint = endpoint or os.getenv("OLLAMA_API_ENDPOINT") or self._default_endpoint()
        self.timeout_seconds = timeout_seconds
        self.transport = transport or UrlLibTransport()

    def propose(self, root: Path, goal: str) -> ChangePlan:
        context = read_repo_context(root)
        prompt = build_planner_prompt(context, goal)
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": {"temperature": 0.1},
        }
        headers = {"Content-Type": "application/json"}
        if self.api_key and self.endpoint.startswith("https://ollama.com/"):
            headers["Authorization"] = f"Bearer {self.api_key}"
        raw = self.transport.generate(self.endpoint, payload, headers, self.timeout_seconds)
        content = raw.get("response")
        if not isinstance(content, str) or not content.strip():
            raise ValueError("Ollama planner response did not include JSON text")
        try:
            data = json.loads(content)
        except json.JSONDecodeError as error:
            raise ValueError(f"Ollama planner returned invalid JSON: {error}") from error
        return plan_from_dict(data)

    def _default_endpoint(self) -> str:
        if self.api_key:
            return "https://ollama.com/api/generate"
        return "http://localhost:11434/api/generate"


def build_planner_prompt(context: RepoContext, goal: str) -> str:
    files = "\n".join(f"- {path}" for path in context.tracked_files[:160])
    commits = "\n".join(f"- {commit}" for commit in context.recent_commits[:8])
    status = "\n".join(f"- {line}" for line in context.status) or "- clean"
    schema = {
        "title": "short concrete title",
        "rationale": "why this advances the Level 5 objective",
        "target": "primary file or capability target",
        "operations": [
            {
                "kind": "replace_text | write_file | append_file",
                "path": "relative/path.py",
                "old": "required for replace_text",
                "new": "required for replace_text",
                "content": "required for write_file or append_file",
            }
        ],
        "verification_command": ["python", "-m", "unittest", "discover", "-s", "tests"],
    }
    return "\n".join([
        "You are the APEX V2 planner.",
        "Return exactly one JSON object and no markdown.",
        "Your plan will be schema-validated before any file is changed.",
        "Plan one small, reversible source or test code improvement.",
        "Do not propose memory-only, log-only, dashboard-only, or proposal-only changes.",
        "Use only relative paths inside the repository.",
        "Prefer replace_text for existing files. Include exact old text for replace_text.",
        "Do not use shell commands. Do not ask to commit. The system handles verification and commit.",
        "",
        "System objective:",
        context.objective_directive,
        "",
        f"User goal: {goal}",
        "",
        f"Branch: {context.branch}",
        "Working tree status:",
        status,
        "",
        "Recent commits:",
        commits or "- none",
        "",
        "Tracked files:",
        files or "- none",
        "",
        "Required JSON schema shape:",
        json.dumps(schema, indent=2),
    ])


def plan_to_json(plan: ChangePlan) -> str:
    return json.dumps(asdict(plan), indent=2)

