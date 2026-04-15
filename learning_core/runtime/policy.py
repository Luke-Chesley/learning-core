from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ExecutionPolicy:
    skill_name: str
    skill_version: str
    task_kind: str = "generation"
    temperature: float = 0.2
    max_tokens: int = 4096
    allowed_tools: tuple[str, ...] = field(default_factory=tuple)
    max_attempts: int = 1
    runtime_mode: str | None = None
    autonomy_tier: str = "draft"
    latency_class: str = "interactive"
    tool_families: tuple[str, ...] = field(default_factory=tuple)
    max_loop_steps: int = 0
    repair_attempts: int = 0
