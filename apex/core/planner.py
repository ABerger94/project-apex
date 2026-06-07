from __future__ import annotations

import json
import os
import socket
import urllib.error
import urllib.request
from dataclasses import asdict
from pathlib import Path
from typing import Any, Protocol

from apex.core.context import read_repo_context
from apex.core.memory import EventMemory
from apex.core.models import ChangePlan, RepoContext
from apex.core.plan_loader import plan_from_dict


class PlannerTransport(Protocol):
    def generate(self, endpoint: str, payload: dict, headers: dict[str, str], timeout_seconds: int) -> dict:
        ...

    def list_models(self, endpoint: str, timeout_seconds: int) -> list[str]:
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

    def list_models(self, endpoint: str, timeout_seconds: int) -> list[str]:
        request = urllib.request.Request(endpoint, method="GET")
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            data = json.loads(response.read().decode("utf-8"))
        models = data.get("models", [])
        if not isinstance(models, list):
            return []
        names: list[str] = []
        for model in models:
            if isinstance(model, dict) and isinstance(model.get("name"), str):
                names.append(model["name"])
        return names


class OllamaPlanner:
    def __init__(
        self,
        model: str | None = None,
        endpoint: str | None = None,
        api_key: str | None = None,
        timeout_seconds: int | None = None,
        transport: PlannerTransport | None = None,
    ) -> None:
        self.model = model or os.getenv("OLLAMA_MODEL") or "minimax-m3:cloud"
        self.api_key = api_key if api_key is not None else os.getenv("OLLAMA_API_KEY")
        self.endpoint = endpoint or os.getenv("OLLAMA_API_ENDPOINT") or self._default_endpoint()
        self.timeout_seconds = timeout_seconds or self._default_timeout_seconds()
        self.transport = transport or UrlLibTransport()

    def propose(self, root: Path, goal: str) -> ChangePlan:
        context = read_repo_context(root)
        memory_events = EventMemory(root / "memory" / "events.jsonl").read_recent(12)
        prompt = build_planner_prompt(context, goal, memory_events)
        data = self._generate_json(prompt)
        return plan_from_dict(data)

    def suggest_goals(self, root: Path, limit: int = 3) -> dict:
        context = read_repo_context(root)
        memory_events = EventMemory(root / "memory" / "events.jsonl").read_recent(16)
        prompt = build_goal_suggestion_prompt(context, memory_events, limit)
        data = self._generate_json(prompt)
        goals = data.get("goals")
        if not isinstance(goals, list) or not goals:
            raise ValueError("Ollama goal suggester returned no goals")
        clean_goals = []
        for index, item in enumerate(goals[:limit], start=1):
            if not isinstance(item, dict):
                raise ValueError("Each suggested goal must be an object")
            goal = str(item.get("goal") or "").strip()
            rationale = str(item.get("rationale") or "").strip()
            if not goal or not rationale:
                raise ValueError("Each suggested goal requires goal and rationale")
            clean_goals.append({
                "priority": int(item.get("priority") or index),
                "goal": goal,
                "rationale": rationale,
            })
        return {"goals": clean_goals}

    def _generate_json(self, prompt: str) -> dict:
        model = self._resolved_model()
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": {"temperature": 0.1},
        }
        headers = {"Content-Type": "application/json"}
        if self.api_key and self.endpoint.startswith("https://ollama.com/"):
            headers["Authorization"] = f"Bearer {self.api_key}"
        try:
            raw = self.transport.generate(self.endpoint, payload, headers, self.timeout_seconds)
        except TimeoutError as error:
            raise ValueError(self._timeout_message()) from error
        except socket.timeout as error:
            raise ValueError(self._timeout_message()) from error
        except urllib.error.HTTPError as error:
            raise ValueError(self._http_error_message(error)) from error
        content = raw.get("response")
        if not isinstance(content, str) or not content.strip():
            raise ValueError("Ollama planner response did not include JSON text")
        return parse_planner_json(content)

    def _default_endpoint(self) -> str:
        return "http://localhost:11434/api/generate"

    def _default_timeout_seconds(self) -> int:
        configured = os.getenv("OLLAMA_TIMEOUT_SECONDS")
        if configured:
            try:
                return int(configured)
            except ValueError:
                return 300
        if self.endpoint.startswith("https://ollama.com/"):
            return 300
        return 120

    def _timeout_message(self) -> str:
        return (
            f"Ollama planner timed out after {self.timeout_seconds}s "
            f"using model {self._resolved_model()} at {self.endpoint}. "
            "Try again, reduce the goal scope, or increase OLLAMA_TIMEOUT_SECONDS."
        )

    def _http_error_message(self, error: urllib.error.HTTPError) -> str:
        if error.code == 429:
            retry_after = error.headers.get("Retry-After") if error.headers else None
            retry_detail = f" Retry after {retry_after} seconds." if retry_after else ""
            return (
                f"Ollama planner was rate limited by {self.endpoint} using model {self._resolved_model()}."
                f"{retry_detail} Wait before generating another plan, reduce repeated requests, or switch to "
                "a local Ollama endpoint by clearing OLLAMA_API_ENDPOINT and using a local model."
            )
        return f"Ollama planner HTTP error {error.code} from {self.endpoint}: {error.reason}"

    def _resolved_model(self) -> str:
        if not self._is_local_endpoint():
            return self.model
        if self.model.endswith(":cloud"):
            return self.model
        tags_endpoint = self.endpoint.rsplit("/", 1)[0] + "/tags"
        try:
            models = self.transport.list_models(tags_endpoint, min(self.timeout_seconds, 10))
        except (OSError, urllib.error.URLError, json.JSONDecodeError):
            return self.model
        if not models or self.model in models:
            return self.model
        return models[0]

    def _is_local_endpoint(self) -> bool:
        return self.endpoint.startswith("http://localhost:") or self.endpoint.startswith("http://127.0.0.1:")

    def diagnostic(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "endpoint": self.endpoint,
            "configured_model": self.model,
            "resolved_model": self._resolved_model(),
            "timeout_seconds": self.timeout_seconds,
            "uses_api_key": bool(self.api_key and self.endpoint.startswith("https://ollama.com/")),
        }
        if self._is_local_endpoint():
            tags_endpoint = self.endpoint.rsplit("/", 1)[0] + "/tags"
            try:
                data["available_models"] = self.transport.list_models(tags_endpoint, min(self.timeout_seconds, 10))
            except Exception as error:
                data["model_probe_error"] = str(error)
        return data


def build_planner_prompt(context: RepoContext, goal: str, memory_events: tuple = ()) -> str:
    files = "\n".join(f"- {path}" for path in context.tracked_files[:80])
    commits = "\n".join(f"- {commit}" for commit in context.recent_commits[:5])
    status = "\n".join(f"- {line}" for line in context.status) or "- clean"
    memory = "\n".join(format_memory_event(event) for event in memory_events) or "- none"
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
        "allowed_verification_prefixes": [
            "python -m unittest",
            "python -m py_compile",
            "python -m pytest",
            "node --check",
            "npm test",
            "npm run test",
            "npm run build",
            "git status",
            "git diff",
            "git log",
        ],
    }
    return "\n".join([
        "You are the APEX V2 planner.",
        "Return exactly one strict JSON object and no markdown.",
        "Start the response with { and end it with }.",
        "Do not include comments, trailing commas, single-quoted strings, or unquoted keys.",
        "Your plan will be schema-validated before any file is changed.",
        "Plan one small, reversible source or test code improvement.",
        "Do not propose memory-only, log-only, dashboard-only, or proposal-only changes.",
        "Use only relative paths inside the repository.",
        "Prefer replace_text for existing files. Include exact old text for replace_text.",
        "Shell commands are allowed only as verification_command values with approved non-destructive prefixes.",
        "Do not use shell metacharacters, redirection, pipes, multiline commands, or destructive commands.",
        "Do not ask to commit. The system handles verification and commit.",
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
        "Recent memory events:",
        memory,
        "",
        "Tracked files:",
        files or "- none",
        "",
        "Required JSON schema shape:",
        json.dumps(schema, indent=2),
    ])


def build_goal_suggestion_prompt(context: RepoContext, memory_events: tuple = (), limit: int = 3) -> str:
    files = "\n".join(f"- {path}" for path in context.tracked_files[:80])
    commits = "\n".join(f"- {commit}" for commit in context.recent_commits[:8])
    status = "\n".join(f"- {line}" for line in context.status) or "- clean"
    memory = "\n".join(format_memory_event(event) for event in memory_events) or "- none"
    schema = {
        "goals": [
            {
                "priority": 1,
                "goal": "one concrete next cycle objective",
                "rationale": "why this is the highest-leverage next step toward L5",
            }
        ]
    }
    return "\n".join([
        "You are the APEX V2 autonomy goal selector.",
        "Return exactly one strict JSON object and no markdown.",
        "Start the response with { and end it with }.",
        "Do not include comments, trailing commas, single-quoted strings, or unquoted keys.",
        f"Propose {limit} concrete next cycle goals, ordered by priority.",
        "Each goal must be actionable by one small code/test improvement cycle.",
        "Favor goals that close gaps exposed by recent memory and move toward Level 5 Organizer behavior.",
        "Do not propose vague goals, pure documentation goals, dashboard-only goals, or goals requiring unsafe commands.",
        "",
        "System objective:",
        context.objective_directive,
        "",
        f"Branch: {context.branch}",
        "Working tree status:",
        status,
        "",
        "Recent commits:",
        commits or "- none",
        "",
        "Recent memory events:",
        memory,
        "",
        "Tracked files:",
        files or "- none",
        "",
        "Required JSON schema shape:",
        json.dumps(schema, indent=2),
    ])


def plan_to_json(plan: ChangePlan) -> str:
    return json.dumps(asdict(plan), indent=2)


def parse_planner_json(content: str) -> dict:
    text = content.strip()
    decoder = json.JSONDecoder()
    try:
        data, _ = decoder.raw_decode(text)
    except json.JSONDecodeError:
        data = None
    if isinstance(data, dict):
        return data

    start = text.find("{")
    if start == -1:
        raise ValueError("Ollama planner response did not contain a JSON object")
    try:
        data, _ = decoder.raw_decode(text[start:])
    except json.JSONDecodeError as error:
        excerpt = invalid_json_excerpt(text[start:], error.pos)
        raise ValueError(f"Ollama planner returned invalid JSON near: {excerpt}") from error
    if not isinstance(data, dict):
        raise ValueError("Ollama planner JSON root must be an object")
    return data


def invalid_json_excerpt(text: str, pos: int, radius: int = 160) -> str:
    start = max(0, pos - radius)
    end = min(len(text), pos + radius)
    excerpt = text[start:end].replace("\n", "\\n")
    if start > 0:
        excerpt = "..." + excerpt
    if end < len(text):
        excerpt += "..."
    return excerpt


def format_memory_event(event: Any) -> str:
    data = getattr(event, "data", {}) or {}
    event_type = getattr(event, "event_type", "unknown")
    timestamp = getattr(event, "timestamp", "")
    title = data.get("title") or data.get("goal") or ""
    reason = data.get("reason") or data.get("error") or ""
    accepted = data.get("accepted")
    target = data.get("target") or ""
    operation_count = data.get("operation_count")
    pieces = [str(event_type)]
    if title:
        pieces.append(f"title={title}")
    if target:
        pieces.append(f"target={target}")
    if operation_count is not None:
        pieces.append(f"operations={operation_count}")
    if accepted is not None:
        pieces.append(f"accepted={accepted}")
    if reason:
        pieces.append(f"reason={reason}")
    return f"- {timestamp} " + "; ".join(pieces)
