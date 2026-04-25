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

SkillInstructionalRole = Literal[
    "orientation",
    "setup",
    "safety",
    "concept",
    "procedure",
    "integration",
    "application",
    "review",
]

LearnerPriorKnowledge = Literal["unknown", "novice", "intermediate", "advanced"]
ProgressionEdgeKind = Literal["hardPrerequisite", "recommendedBefore", "revisitAfter", "coPractice"]


def _detect_hard_prerequisite_cycle(edges: list[tuple[str, str]]) -> bool:
    adjacency: dict[str, list[str]] = {}
    indegree: dict[str, int] = {}

    for source, target in edges:
        adjacency.setdefault(source, []).append(target)
        adjacency.setdefault(target, [])
        indegree[target] = indegree.get(target, 0) + 1
        indegree.setdefault(source, 0)

    queue = [node for node, degree in indegree.items() if degree == 0]
    visited = 0

    while queue:
        node = queue.pop()
        visited += 1
        for neighbor in adjacency.get(node, []):
            indegree[neighbor] -= 1
            if indegree[neighbor] == 0:
                queue.append(neighbor)

    return visited != len(indegree)


class ProgressionEdge(StrictModel):
    fromSkillRef: str
    toSkillRef: str
    kind: ProgressionEdgeKind


class ProgressionPhase(StrictModel):
    title: str
    description: str | None = None
    skillRefs: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_phase(self) -> "ProgressionPhase":
        if not self.skillRefs:
            raise ValueError("ProgressionPhase requires at least one skillRef.")
        return self


class ProgressionArtifact(StrictModel):
    phases: list[ProgressionPhase] = Field(default_factory=list)
    edges: list[ProgressionEdge] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_progression(self) -> "ProgressionArtifact":
        if not self.phases:
            raise ValueError("ProgressionArtifact requires at least one phase.")

        seen_skill_refs: set[str] = set()
        for phase in self.phases:
            for skill_ref in phase.skillRefs:
                if skill_ref in seen_skill_refs:
                    raise ValueError(
                        f'ProgressionArtifact assigns duplicate skillRef across phases: "{skill_ref}"',
                    )
                seen_skill_refs.add(skill_ref)

        seen_edges: set[tuple[str, str]] = set()
        hard_prerequisites: list[tuple[str, str]] = []
        for edge in self.edges:
            if edge.fromSkillRef == edge.toSkillRef:
                raise ValueError(
                    f'ProgressionArtifact contains self-loop edge: "{edge.fromSkillRef}"',
                )

            edge_key = (edge.fromSkillRef, edge.toSkillRef)
            if edge_key in seen_edges:
                raise ValueError(
                    "ProgressionArtifact contains duplicate edge "
                    f'"{edge.fromSkillRef}" -> "{edge.toSkillRef}"',
                )
            seen_edges.add(edge_key)

            if edge.kind == "hardPrerequisite":
                hard_prerequisites.append((edge.fromSkillRef, edge.toSkillRef))

        if _detect_hard_prerequisite_cycle(hard_prerequisites):
            raise ValueError("ProgressionArtifact hardPrerequisite edges must be acyclic.")

        return self


class SkillCatalogItem(StrictModel):
    skillRef: str
    title: str
    domainTitle: str | None = None
    strandTitle: str | None = None
    goalGroupTitle: str | None = None
    ordinal: int | None = None
    unitRef: str | None = None
    unitTitle: str | None = None
    unitOrderIndex: int | None = None
    instructionalRole: SkillInstructionalRole | None = None
    requiresAdultSupport: bool | None = None
    safetyCritical: bool | None = None
    isAuthenticApplication: bool | None = None


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
    gradeLevels: list[str] = Field(default_factory=list)
    learnerPriorKnowledge: LearnerPriorKnowledge | None = None
    totalWeeks: int | None = None
    sessionsPerWeek: int | float | None = None
    sessionMinutes: int | None = None
    totalSessions: int | None = None
    suggestedPhaseCountMin: int | None = None
    suggestedPhaseCountMax: int | None = None
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
