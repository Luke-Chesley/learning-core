from __future__ import annotations

from typing import Literal

from pydantic import Field

from learning_core.contracts.base import StrictModel


class ProgressionNode(StrictModel):
    id: str
    title: str
    description: str | None = None


class ProgressionEdge(StrictModel):
    sourceId: str
    targetId: str
    relation: Literal["prerequisite", "recommended_after", "supports"]


class ProgressionArtifact(StrictModel):
    schemaVersion: Literal["1"]
    title: str
    nodes: list[ProgressionNode] = Field(default_factory=list)
    edges: list[ProgressionEdge] = Field(default_factory=list)


class ProgressionGenerationRequest(StrictModel):
    curriculumTitle: str
    subject: str
    learningGoals: list[str] = Field(default_factory=list)


class ProgressionRevisionRequest(StrictModel):
    currentArtifact: ProgressionArtifact
    revisionRequest: str

