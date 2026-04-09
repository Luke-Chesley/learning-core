from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import Field

from learning_core.contracts.base import StrictModel
from learning_core.contracts.operation import OperationEnvelope


class PromptPreview(StrictModel):
    system_prompt: str
    user_prompt: str


class ExecutionLineage(StrictModel):
    operation_name: str
    skill_name: str
    skill_version: str
    provider: str
    model: str
    executed_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ExecutionTrace(StrictModel):
    request_id: str
    operation_name: str
    allowed_tools: list[str]
    prompt_preview: PromptPreview
    request_envelope: OperationEnvelope
    executed_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    agent_trace: dict[str, Any] | None = None
