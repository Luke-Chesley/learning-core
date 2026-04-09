from __future__ import annotations

from typing import Literal

from pydantic import Field

from learning_core.contracts.base import StrictModel


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


class ProgressionGenerationRequest(StrictModel):
    learnerName: str
    sourceTitle: str
    sourceSummary: str | None = None
    skillCatalog: list[SkillCatalogItem] = Field(default_factory=list)


class ProgressionRevisionRequest(StrictModel):
    learnerName: str
    sourceTitle: str
    sourceSummary: str | None = None
    skillCatalog: list[SkillCatalogItem] = Field(default_factory=list)
    revisionRequest: str | None = None
