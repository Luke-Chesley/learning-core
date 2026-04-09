from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from learning_core.runtime.errors import ConfigurationError


ToolHandler = Callable[..., Any]


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    description: str
    handler: ToolHandler


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, ToolDefinition] = {}

    def register(self, tool: ToolDefinition) -> None:
        self._tools[tool.name] = tool

    def resolve_many(self, tool_names: tuple[str, ...]) -> list[ToolDefinition]:
        missing = [name for name in tool_names if name not in self._tools]
        if missing:
            raise ConfigurationError(f"Unknown tool(s) requested by skill: {', '.join(missing)}")
        return [self._tools[name] for name in tool_names]

