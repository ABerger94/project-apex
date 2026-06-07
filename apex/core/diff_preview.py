from __future__ import annotations

import difflib
from pathlib import Path

from apex.core.models import ChangePlan, FileOperation
from apex.core.patcher import Patcher


def build_plan_preview(root: Path, plan: ChangePlan) -> dict:
    root = root.resolve()
    patcher = Patcher(root)
    files = []
    errors = []
    for operation in plan.operations:
        try:
            path = patcher._resolve(operation.path)
            old_text, new_text = preview_text(path, operation)
            relative = str(path.relative_to(root)).replace("\\", "/")
            files.append({
                "path": relative,
                "kind": operation.kind,
                "diff": unified_diff(relative, old_text, new_text),
            })
        except Exception as error:
            errors.append({"path": operation.path, "kind": operation.kind, "error": str(error)})
    return {
        "files": files,
        "errors": errors,
    }


def preview_text(path: Path, operation: FileOperation) -> tuple[str, str]:
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    if operation.kind == "write_file":
        return existing, operation.content
    if operation.kind == "append_file":
        return existing, existing + operation.content
    if operation.kind == "replace_text":
        if operation.old not in existing:
            raise ValueError("replacement text not found")
        return existing, existing.replace(operation.old, operation.new, 1)
    raise ValueError(f"unsupported operation kind: {operation.kind}")


def unified_diff(path: str, old_text: str, new_text: str) -> str:
    return "".join(difflib.unified_diff(
        old_text.splitlines(keepends=True),
        new_text.splitlines(keepends=True),
        fromfile=f"a/{path}",
        tofile=f"b/{path}",
    ))
