from __future__ import annotations

from pathlib import Path

from apex.core.models import ChangePlan, PatchResult


class Patcher:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()

    def apply(self, plan: ChangePlan) -> PatchResult:
        changed: list[Path] = []
        for operation in plan.operations:
            path = self._resolve(operation.path)
            path.parent.mkdir(parents=True, exist_ok=True)
            if operation.kind == "write_file":
                path.write_text(operation.content, encoding="utf-8")
            elif operation.kind == "append_file":
                existing = path.read_text(encoding="utf-8") if path.exists() else ""
                path.write_text(existing + operation.content, encoding="utf-8")
            elif operation.kind == "replace_text":
                text = path.read_text(encoding="utf-8")
                if operation.old not in text:
                    raise ValueError(f"Replacement text not found in {operation.path}")
                path.write_text(text.replace(operation.old, operation.new, 1), encoding="utf-8")
            else:
                raise ValueError(f"Unsupported operation kind: {operation.kind}")
            changed.append(path)
        return PatchResult(changed_paths=tuple(dict.fromkeys(changed)))

    def _resolve(self, relative_path: str) -> Path:
        clean = relative_path.replace("\\", "/")
        if clean.startswith("/") or ".." in clean.split("/"):
            raise ValueError(f"Unsafe path: {relative_path}")
        path = (self.root / clean).resolve()
        try:
            path.relative_to(self.root)
        except ValueError as error:
            raise ValueError(f"Path escapes repository: {relative_path}") from error
        return path

