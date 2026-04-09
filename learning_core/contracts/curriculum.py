from __future__ import annotations

from typing import Literal

from pydantic import Field

from learning_core.contracts.base import StrictModel


class CurriculumGoal(StrictModel):
    id: str
    title: str
    description: str | None = None


class CurriculumLesson(StrictModel):
    id: str
    title: str
    objective: str


class CurriculumUnit(StrictModel):
    id: str
    title: str
    lessons: list[CurriculumLesson] = Field(default_factory=list)


class CurriculumArtifact(StrictModel):
    schemaVersion: Literal["1"]
    title: str
    subject: str
    gradeBand: str | None = None
    goals: list[CurriculumGoal] = Field(default_factory=list)
    units: list[CurriculumUnit] = Field(default_factory=list)


class CurriculumGenerationRequest(StrictModel):
    learnerName: str
    gradeLevel: str | None = None
    subjects: list[str] = Field(default_factory=list)
    familyContext: str | None = None
    constraints: list[str] = Field(default_factory=list)


class CurriculumRevisionRequest(StrictModel):
    currentArtifact: CurriculumArtifact
    revisionRequest: str
    preserve: list[str] = Field(default_factory=list)


class CurriculumUpdateProposalChange(StrictModel):
    path: str
    changeType: Literal["add", "remove", "replace", "resequence"]
    rationale: str


class CurriculumUpdateProposalArtifact(StrictModel):
    schemaVersion: Literal["1"]
    summary: str
    rationale: list[str] = Field(default_factory=list)
    proposedChanges: list[CurriculumUpdateProposalChange] = Field(default_factory=list)


class CurriculumUpdateProposalRequest(StrictModel):
    evaluationSummary: str
    curriculumTitle: str | None = None
    progressionTitle: str | None = None
    constraints: list[str] = Field(default_factory=list)
