from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class RuntimePackDefinition:
    name: str
    category: str
    prompt_sections: tuple[str, ...] = ()
    tool_families: tuple[str, ...] = ()
    metadata: dict[str, str] = field(default_factory=dict)

