from __future__ import annotations

from typing import Literal

from pydantic import Field

from learning_core.contracts.base import StrictModel
from learning_core.contracts.source_interpret import (
    SourceContinuationMode,
    SourceDeliveryPattern,
    SourceEntryStrategy,
    SourceInterpretationHorizon,
    SourceKind,
)


class ProgressionEdge(StrictModel):
    fromSkillRef: str
    toSkillRef: str
    kind: Literal["hardPrerequisite", "recommendedBefore", "revisitAfter", "coPractice"]


class ProgressionPhase(StrictModel):
    title: str
    description: str | None = None
    skillRefs: list[str] = Field(default_factory=list)


class ProgressionArtifact(StrictModel):
    phases: list[ProgressionPhase] = Field(default_factory=list)
    edges: list[ProgressionEdge] = Field(default_factory=list)


class SkillCatalogItem(StrictModel):
    skillRef: str
    title: str
    domainTitle: str | None = None
    strandTitle: str | None = None
    goalGroupTitle: str | None = None
    ordinal: int | None = None


ProgressionLessonType = Literal[
    "task",
    "skill_support",
    "concept",
    "setup",
    "reflection",
    "assessment",
]
ProgressionDeliveryPattern = SourceDeliveryPattern
ProgressionRequestMode = Literal["source_entry", "conversation_intake", "curriculum_revision"]


class ProgressionLessonAnchor(StrictModel):
    lessonRef: str
    unitRef: str
    title: str
    lessonType: ProgressionLessonType
    orderIndex: int = Field(ge=1)
    linkedSkillRefs: list[str] = Field(default_factory=list)


class ProgressionLaunchPlan(StrictModel):
    recommendedHorizon: SourceInterpretationHorizon
    scopeSummary: str
    initialSliceUsed: bool
    initialSliceLabel: str | None = None
    entryStrategy: SourceEntryStrategy | None = None
    entryLabel: str | None = None
    continuationMode: SourceContinuationMode | None = None
    openingLessonRefs: list[str] = Field(default_factory=list)
    openingSkillRefs: list[str] = Field(default_factory=list)


class ProgressionBasisRequest(StrictModel):
    learnerName: str
    sourceTitle: str
    sourceSummary: str | None = None
    requestMode: ProgressionRequestMode | None = None
    sourceKind: SourceKind | None = None
    deliveryPattern: ProgressionDeliveryPattern | None = None
    entryStrategy: SourceEntryStrategy | None = None
    continuationMode: SourceContinuationMode | None = None
    launchPlan: ProgressionLaunchPlan | None = None
    skillCatalog: list[SkillCatalogItem] = Field(default_factory=list)
    lessonAnchors: list[ProgressionLessonAnchor] = Field(default_factory=list)


class ProgressionGenerationRequest(ProgressionBasisRequest):
    pass


class ProgressionRevisionRequest(ProgressionBasisRequest):
    revisionRequest: str | None = None
