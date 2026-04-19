from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from learning_core.contracts.base import StrictModel
from learning_core.contracts.source_interpret import (
    SourceContinuationMode,
    SourceDeliveryPattern,
    SourceEntryStrategy,
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


class ProgressionUnitAnchor(StrictModel):
    unitRef: str
    title: str
    description: str
    orderIndex: int = Field(ge=1)
    estimatedWeeks: int | None = None
    estimatedSessions: int | None = None
    skillRefs: list[str] = Field(default_factory=list)


ProgressionRequestMode = Literal["source_entry", "conversation_intake", "curriculum_revision"]


class ProgressionBasisRequest(StrictModel):
    learnerName: str
    sourceTitle: str
    sourceSummary: str | None = None
    requestMode: ProgressionRequestMode | None = None
    sourceKind: SourceKind | None = None
    deliveryPattern: SourceDeliveryPattern | None = None
    entryStrategy: SourceEntryStrategy | None = None
    continuationMode: SourceContinuationMode | None = None
    skillCatalog: list[SkillCatalogItem] = Field(default_factory=list)
    unitAnchors: list[ProgressionUnitAnchor] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_basis(self) -> "ProgressionBasisRequest":
        if not self.skillCatalog:
            raise ValueError("progression_generate requires a non-empty skillCatalog.")
        return self


class ProgressionGenerationRequest(ProgressionBasisRequest):
    pass


class ProgressionRevisionRequest(ProgressionBasisRequest):
    revisionRequest: str | None = None
