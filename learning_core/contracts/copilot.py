from __future__ import annotations

from typing import Any, Literal

from pydantic import Field

from learning_core.contracts.base import StrictModel


class CopilotChatMessage(StrictModel):
    role: Literal["user", "assistant", "system"]
    content: str


class CopilotChatContext(StrictModel):
    learnerId: str | None = None
    learnerName: str | None = None
    curriculumSourceId: str | None = None
    lessonId: str | None = None
    standardIds: list[str] = Field(default_factory=list)
    goalIds: list[str] = Field(default_factory=list)
    curriculumSnapshot: dict[str, Any] | None = None
    dailyWorkspaceSnapshot: dict[str, Any] | None = None
    weeklyPlanningSnapshot: dict[str, Any] | None = None
    feedbackNotes: list[str] = Field(default_factory=list)
    recentOutcomes: list[dict[str, Any]] = Field(default_factory=list)


class CopilotChatRequest(StrictModel):
    messages: list[CopilotChatMessage] = Field(default_factory=list)
    context: CopilotChatContext | None = None


class CopilotChatArtifact(StrictModel):
    answer: str
