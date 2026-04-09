from __future__ import annotations

from typing import Any

from pydantic import Field

from learning_core.contracts.base import StrictModel
from learning_core.contracts.lesson_draft import StructuredLessonDraft


class LessonDraftResolvedTiming(StrictModel):
    resolvedTotalMinutes: int
    sourceSessionMinutes: int | None = None
    lessonOverrideMinutes: int | None = None
    timingSource: str


class LessonDraftRouteItem(StrictModel):
    title: str
    subject: str
    estimatedMinutes: int
    objective: str
    lessonLabel: str
    note: str | None = None


class TeacherContext(StrictModel):
    subject_comfort: str | None = None
    prep_tolerance: str | None = None
    teaching_style: str | None = None
    role: str | None = None


class SessionPlanGenerationRequest(StrictModel):
    title: str | None = None
    topic: str
    resolvedTiming: LessonDraftResolvedTiming | None = None
    objectives: list[str] = Field(default_factory=list)
    routeItems: list[LessonDraftRouteItem] = Field(default_factory=list)
    materials: list[str] = Field(default_factory=list)
    lessonShape: str | None = None
    teacherContext: TeacherContext | None = None
    context: dict[str, Any] | None = None


SessionPlanArtifact = StructuredLessonDraft
