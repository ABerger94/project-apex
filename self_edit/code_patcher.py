from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path


class PatchError(Exception):
    pass


@dataclass
class CodePatch:
    target_file: str    # path relative to project root
    mode: str           # "append" | "insert_after_imports"
    code: str           # Python source to add


def apply_patch(root: Path, patch: CodePatch) -> Path:
    """Apply patch to the target file and return the path. Raises PatchError on failure."""
    target = root / patch.target_file
    if not target.exists():
        raise PatchError(f"Target file not found: {patch.target_file}")

    original = target.read_text(encoding="utf-8")

    if patch.mode == "append":
        new_content = _append(original, patch.code)
    elif patch.mode == "insert_after_imports":
        new_content = _insert_after_imports(original, patch.code)
    else:
        raise PatchError(f"Unknown patch mode: {patch.mode!r}")

    _validate_syntax(new_content, patch.target_file)
    target.write_text(new_content, encoding="utf-8")
    return target


def _append(content: str, code: str) -> str:
    return content.rstrip() + "\n\n\n" + code.strip() + "\n"


def _insert_after_imports(content: str, code: str) -> str:
    lines = content.splitlines(keepends=True)
    last_import = 0
    for i, line in enumerate(lines):
        stripped = line.lstrip()
        if stripped.startswith("import ") or (stripped.startswith("from ") and " import " in stripped):
            last_import = i + 1
    if last_import == 0:
        return _append(content, code)
    inserted = lines[:last_import] + ["\n\n" + code.strip() + "\n\n"] + lines[last_import:]
    return "".join(inserted)


def _validate_syntax(content: str, label: str) -> None:
    try:
        ast.parse(content)
    except SyntaxError as exc:
        raise PatchError(f"Syntax error in {label} after patching: {exc}") from exc
