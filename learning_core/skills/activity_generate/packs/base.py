from __future__ import annotations

from typing import Protocol, runtime_checkable

from langchain_core.tools import BaseTool


@runtime_checkable
class Pack(Protocol):
    """A subject pack that owns keywords, prompt docs, and tools for activity_generate."""

    @property
    def name(self) -> str: ...

    @property
    def keywords(self) -> tuple[str, ...]: ...

    def prompt_sections(self) -> list[str]:
        """Return markdown doc sections to append to the user prompt when this pack is active."""
        ...

    def tools(self) -> list[BaseTool]:
        """Return LangChain tools this pack exposes to the agent loop."""
        ...
