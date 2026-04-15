from __future__ import annotations

from typing import Any

from pydantic import Field

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
