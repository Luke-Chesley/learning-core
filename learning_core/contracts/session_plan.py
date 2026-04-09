from __future__ import annotations

from typing import Literal

from pydantic import Field

from learning_core.contracts.base import StrictModel
from learning_core.contracts.lesson_draft import StructuredLessonDraft


class SessionBlock(StrictModel):
    id: str
    title: str
    minutes: int
    blockType: str
    purpose: str


class SessionPlanArtifact(StrictModel):
    schemaVersion: Literal["1"]
    title: str
    learnerName: str
    totalMinutes: int
    blocks: list[SessionBlock] = Field(default_factory=list)


class SessionPlanGenerationRequest(StrictModel):
    learnerName: str
    lessonDraft: StructuredLessonDraft
    workflowMode: str | None = None
    subject: str | None = None

