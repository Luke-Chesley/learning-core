from __future__ import annotations

from typing import Literal

from pydantic import Field

from learning_core.contracts.base import StrictModel


class EvidenceObservation(StrictModel):
    source: str
    summary: str
    score: float | None = None


class EvaluationArtifact(StrictModel):
    schemaVersion: Literal["1"]
    sessionId: str
    rating: Literal["needs_more_work", "partial", "successful", "exceeded"]
    summary: str
    evidence: list[EvidenceObservation] = Field(default_factory=list)
    nextActions: list[str] = Field(default_factory=list)


class SessionEvaluationRequest(StrictModel):
    sessionId: str
    learnerName: str
    lessonTitle: str
    evidence: list[EvidenceObservation] = Field(default_factory=list)

