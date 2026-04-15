from __future__ import annotations

from learning_core.contracts.copilot import CopilotChatArtifact
from learning_core.response_types.base import ResponseTypeDefinition


SUMMARY_RESPONSE_TYPE = ResponseTypeDefinition(
    name="summary",
    artifact_model=CopilotChatArtifact,
    response_mode="text",
    artifact_factory=lambda raw_text: CopilotChatArtifact(answer=raw_text.strip()),
    description="Text answer wrapped in the standard copilot chat artifact.",
)
