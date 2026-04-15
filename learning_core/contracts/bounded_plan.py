from __future__ import annotations

from typing import Any

from pydantic import Field, model_validator

from learning_core.contracts.base import StrictModel
from learning_core.contracts.progression import ProgressionArtifact
from learning_core.contracts.source_interpret import (
    RequestedIntakeRoute,
    SourceInterpretationHorizon,
    SourceKind,
)


class BoundedPlanLesson(StrictModel):
    title: str
    description: str
    subject: str | None = None
    estimatedMinutes: int | None = None
    materials: list[str] = Field(default_factory=list)
    objectives: list[str] = Field(default_factory=list)
    linkedSkillTitles: list[str] = Field(default_factory=list)


class BoundedPlanUnit(StrictModel):
    title: str
    description: str
    estimatedWeeks: int | None = None
    estimatedSessions: int | None = None
    lessons: list[BoundedPlanLesson] = Field(default_factory=list, min_length=1)


class BoundedPlanGenerationRequest(StrictModel):
    learnerName: str
    requestedRoute: RequestedIntakeRoute
    routedRoute: RequestedIntakeRoute
    sourceKind: SourceKind
    chosenHorizon: SourceInterpretationHorizon
    sourceText: str = Field(min_length=1)
    titleCandidate: str | None = None
    detectedChunks: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)


class BoundedPlanArtifact(StrictModel):
    title: str
    description: str
    subjects: list[str] = Field(default_factory=list)
    horizon: SourceInterpretationHorizon
    rationale: list[str] = Field(default_factory=list)
    document: dict[str, Any]
    units: list[BoundedPlanUnit] = Field(default_factory=list, min_length=1)
    progression: ProgressionArtifact | None = None
    suggestedSessionMinutes: int | None = None

    @model_validator(mode="before")
    @classmethod
    def ensure_document(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value

        document = value.get("document")
        if isinstance(document, dict) and document:
            return value

        subjects = value.get("subjects")
        fallback_subject = (
            subjects[0]
            if isinstance(subjects, list) and len(subjects) > 0 and isinstance(subjects[0], str)
            else "Integrated Studies"
        )
        document_map: dict[str, dict[str, list[str]]] = {}

        for unit in value.get("units", []):
            if not isinstance(unit, dict):
                continue

            unit_title = unit.get("title")
            if not isinstance(unit_title, str) or not unit_title.strip():
                continue

            lessons = unit.get("lessons", [])
            grouped_titles: dict[str, list[str]] = {}

            if isinstance(lessons, list):
                for lesson in lessons:
                    if not isinstance(lesson, dict):
                        continue

                    lesson_title = lesson.get("title")
                    if not isinstance(lesson_title, str) or not lesson_title.strip():
                        continue

                    subject = lesson.get("subject")
                    subject_key = (
                        subject if isinstance(subject, str) and subject.strip() else fallback_subject
                    )
                    grouped_titles.setdefault(subject_key, []).append(lesson_title)

            if not grouped_titles:
                grouped_titles[fallback_subject] = [unit_title]

            for subject_key, lesson_titles in grouped_titles.items():
                subject_document = document_map.setdefault(subject_key, {})
                subject_document[unit_title] = lesson_titles

        value["document"] = document_map
        return value
