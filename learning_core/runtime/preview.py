from __future__ import annotations

from dataclasses import dataclass

from learning_core.observability.traces import PromptPreview


@dataclass(frozen=True)
class KernelPreview:
    prompt_preview: PromptPreview
    task_profile: str
    response_type: str
    workflow_card: str
    runtime_mode: str
    selected_packs: list[str]
    tool_families: list[str]
    allowed_tools: list[str]
