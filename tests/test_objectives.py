from __future__ import annotations

import json
from pathlib import Path

from apex_loop import ensure_objectives
from config import CONFIG


def test_ensure_objectives_creates_file():
    obj_path = CONFIG.root / "memory" / "objectives.json"
    if obj_path.exists():
        obj_path.unlink()

    objectives = ensure_objectives()
    assert isinstance(objectives, list)
    assert len(objectives) >= 1
    assert obj_path.exists()
    data = json.loads(obj_path.read_text(encoding="utf-8"))
    assert isinstance(data, list)


def test_regenerates_when_all_completed(tmp_path, monkeypatch):
    # Ensure we operate on a temp copy of the project's root to avoid changing real workspace files.
    project_root = tmp_path / "proj"
    project_root.mkdir()
    # Monkeypatch CONFIG.root to the temp project root
    import importlib
    import config as config_module

    # Reload config to ensure CONFIG is bound to the correct path if needed
    importlib.reload(config_module)
    monkeypatch.setattr(config_module, "ROOT", project_root)
    monkeypatch.setattr(config_module, "CONFIG", config_module.ApexConfig(root=project_root))

    # Create an objectives file where all entries are completed
    objectives_dir = project_root / "memory"
    objectives_dir.mkdir(parents=True)
    initial = [
        {"id": 1, "title": "foo", "completed": True},
        {"id": 2, "title": "bar", "completed": True},
    ]
    (objectives_dir / "objectives.json").write_text(json.dumps(initial), encoding="utf-8")

    # Call ensure_objectives and confirm it returns a fresh set with at least one incomplete
    from apex_loop import ensure_objectives

    new_objs = ensure_objectives()
    assert isinstance(new_objs, list)
    assert any(not o.get("completed") for o in new_objs)
