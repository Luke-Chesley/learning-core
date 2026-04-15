from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from learning_core.observability.traces import PromptPreview


PromptPreviewBuilder = Callable[[Any, Any, Any, list[Any]], PromptPreview]


@dataclass(frozen=True)
class WorkflowCardDefinition:
    name: str
    supported_task_profiles: tuple[str, ...]
    supported_response_types: tuple[str, ...]
    prompt_preview_builder: PromptPreviewBuilder
    allowed_tool_families: tuple[str, ...] = field(default_factory=tuple)
    pack_categories: tuple[str, ...] = field(default_factory=tuple)

    def build_prompt_preview(self, payload: Any, context: Any, runtime_request: Any, selected_packs: list[Any]) -> PromptPreview:
        return self.prompt_preview_builder(payload, context, runtime_request, selected_packs)
