from __future__ import annotations

from typing import Literal

from pydantic import Field

from learning_core.contracts.base import StrictModel


class LessonAdaptation(StrictModel):
    trigger: str
    action: str


class LessonBlock(StrictModel):
    type: str
    title: str
    minutes: int
    purpose: str
    teacher_action: str
    learner_action: str
    check_for: str | None = None
    materials_needed: list[str] = Field(default_factory=list)
    optional: bool = False


class StructuredLessonDraft(StrictModel):
    schema_version: Literal["1.0"]
    title: str
    lesson_focus: str
    primary_objectives: list[str] = Field(default_factory=list)
    success_criteria: list[str] = Field(default_factory=list)
    total_minutes: int
    blocks: list[LessonBlock] = Field(default_factory=list)
    materials: list[str] = Field(default_factory=list)
    teacher_notes: list[str] = Field(default_factory=list)
    adaptations: list[LessonAdaptation] = Field(default_factory=list)
    assessment_artifact: str | None = None
    lesson_shape: str | None = None
    prep: list[str] = Field(default_factory=list)
    extension: str | None = None
    follow_through: str | None = None
    accommodations: list[str] = Field(default_factory=list)

