from __future__ import annotations

from typing import Any

from pydantic import Field

from learning_core.contracts.base import StrictModel
from learning_core.contracts.operation import OperationEnvelope
from learning_core.observability.traces import ExecutionLineage, ExecutionTrace, PromptPreview


class OperationDescriptor(StrictModel):
    operation_name: str
    skill_name: str
    skill_version: str
    task_kind: str
    allowed_tools: list[str] = Field(default_factory=list)


class OperationPromptPreviewResponse(StrictModel):
    operation_name: str
    skill_name: str
    skill_version: str
    request_id: str
    allowed_tools: list[str] = Field(default_factory=list)
    system_prompt: str
    user_prompt: str
    request_envelope: OperationEnvelope


class OperationExecuteResponse(StrictModel):
    operation_name: str
    artifact: dict[str, Any]
    lineage: ExecutionLineage
    trace: ExecutionTrace
    prompt_preview: PromptPreview | None = None
