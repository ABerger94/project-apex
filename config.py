from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path


ROOT = Path(__file__).resolve().parent


@dataclass(frozen=True)
class LevelDefinition:
    name: str
    target_score: float
    description: str


@dataclass(frozen=True)
class Base44Config:
    app_id: str | None = os.getenv("BASE44_APP_ID") or os.getenv("VITE_BASE44_APP_ID")
    app_base_url: str | None = os.getenv("BASE44_APP_BASE_URL") or os.getenv("VITE_BASE44_APP_BASE_URL")
    access_token: str | None = os.getenv("BASE44_ACCESS_TOKEN")
    provider: str = os.getenv("APEX_ORACLE_PROVIDER", "local").lower()

    @property
    def enabled(self) -> bool:
        return self.provider == "base44" and bool(self.app_id)


@dataclass(frozen=True)
class SandboxConfig:
    timeout_seconds: int = int(os.getenv("APEX_SANDBOX_TIMEOUT_SECONDS", "30"))
    test_command: tuple[str, ...] = (sys.executable, "-m", "unittest", "discover", "-s", "tests")
    proposal_dir: Path = ROOT / "self_edit" / "proposals"


@dataclass(frozen=True)
class ApexConfig:
    root: Path = ROOT
    memory_log: Path = ROOT / "memory" / "episodic_log.jsonl"
    max_cycles: int = int(os.getenv("APEX_MAX_CYCLES", "1"))
    base44: Base44Config = field(default_factory=Base44Config)
    sandbox: SandboxConfig = field(default_factory=SandboxConfig)
    levels: dict[str, LevelDefinition] = field(default_factory=lambda: {
        "L3": LevelDefinition(
            name="Agents",
            target_score=0.70,
            description="Plans, executes, verifies, and logs delegated tasks.",
        ),
        "L4": LevelDefinition(
            name="Innovators",
            target_score=0.80,
            description="Generates useful novel approaches and validates measurable gain.",
        ),
        "L5": LevelDefinition(
            name="Organizers",
            target_score=0.90,
            description="Coordinates multi-step organizational workflows with accountability.",
        ),
    })


CONFIG = ApexConfig()
