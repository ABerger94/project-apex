from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from apex.core.models import ChangePlan, FileOperation


def load_plan(path: Path) -> ChangePlan:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"Invalid JSON plan: {error}") from error
    if not isinstance(data, dict):
        raise ValueError("Plan must be a JSON object")
    return plan_from_dict(data)


def plan_from_dict(data: dict[str, Any]) -> ChangePlan:
    title = _required_string(data, "title")
    rationale = _required_string(data, "rationale")
    target = _required_string(data, "target")
    operations_data = data.get("operations")
    if not isinstance(operations_data, list) or not operations_data:
        raise ValueError("Plan must include at least one operation")

    operations = tuple(_operation_from_dict(item) for item in operations_data)
    command_data = data.get("verification_command")
    if command_data is None:
        verification_command = ("python", "-m", "unittest", "discover", "-s", "tests")
    elif isinstance(command_data, list) and all(isinstance(item, str) and item for item in command_data):
        verification_command = tuple(command_data)
    else:
        raise ValueError("verification_command must be a list of non-empty strings")

    return ChangePlan(
        title=title,
        rationale=rationale,
        target=target,
        operations=operations,
        verification_command=verification_command,
    )


def _operation_from_dict(data: Any) -> FileOperation:
    if not isinstance(data, dict):
        raise ValueError("Each operation must be an object")
    kind = _required_string(data, "kind")
    path = _required_string(data, "path")
    if kind in {"write_file", "append_file"}:
        content = _required_string(data, "content")
        return FileOperation(kind=kind, path=path, content=content)
    if kind == "replace_text":
        old = _required_string(data, "old")
        new = _required_string(data, "new")
        return FileOperation(kind=kind, path=path, old=old, new=new)
    raise ValueError(f"Unsupported operation kind: {kind}")


def _required_string(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} must be a non-empty string")
    return value

