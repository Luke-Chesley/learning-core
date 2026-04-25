from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from learning_core.contracts.base import StrictModel
from learning_core.contracts.progression import ProgressionArtifact, SkillCatalogItem
from learning_core.contracts.source_interpret import (
    SourceContinuationMode,
    SourceDeliveryPattern,
    SourceEntryStrategy,
    SourceInterpretationHorizon,
    SourceKind,
)


class LaunchPlanUnitAnchor(StrictModel):
    unitRef: str
    title: str
    description: str
    orderIndex: int = Field(ge=1)
    estimatedWeeks: int | None = None
    estimatedSessions: int | None = None
    skillRefs: list[str] = Field(default_factory=list)


class LaunchPlanGenerationRequest(StrictModel):
    learnerName: str
    sourceTitle: str
    sourceSummary: str | None = None
    requestMode: Literal["source_entry", "conversation_intake", "curriculum_revision"] | None = None
    sourceKind: SourceKind | None = None
    deliveryPattern: SourceDeliveryPattern | None = None
    entryStrategy: SourceEntryStrategy | None = None
    entryLabel: str | None = None
    continuationMode: SourceContinuationMode | None = None
    chosenHorizon: SourceInterpretationHorizon
    skillCatalog: list[SkillCatalogItem] = Field(default_factory=list)
    unitAnchors: list[LaunchPlanUnitAnchor] = Field(default_factory=list)
    progression: ProgressionArtifact | None = None

    @model_validator(mode="after")
    def validate_basis(self) -> "LaunchPlanGenerationRequest":
        if not self.skillCatalog:
            raise ValueError("launch_plan_generate requires a non-empty skillCatalog.")
        if not self.unitAnchors:
            raise ValueError("launch_plan_generate requires at least one unit anchor.")
        return self


class LaunchPlanArtifact(StrictModel):
    chosenHorizon: SourceInterpretationHorizon
    scopeSummary: str
    initialSliceUsed: bool
    initialSliceLabel: str | None = None
    openingSkillRefs: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_opening_refs(self) -> "LaunchPlanArtifact":
        if not self.openingSkillRefs:
            raise ValueError("LaunchPlanArtifact requires at least one openingSkillRef.")
        return self
