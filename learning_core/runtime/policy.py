from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ExecutionPolicy:
    skill_name: str
    skill_version: str
    temperature: float = 0.2
    max_tokens: int = 4096
    allowed_tools: tuple[str, ...] = field(default_factory=tuple)
    max_attempts: int = 1

