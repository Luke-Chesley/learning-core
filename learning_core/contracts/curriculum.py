from __future__ import annotations

from typing import Any, Literal

from pydantic import Field

from learning_core.contracts.base import StrictModel
from learning_core.contracts.progression import ProgressionArtifact


class CurriculumChatMessage(StrictModel):
    role: Literal["user", "assistant"]
    content: str


class CurriculumCapturedRequirements(StrictModel):
    topic: str = ""
    goals: str = ""
    timeframe: str = ""
    learnerProfile: str = ""
    constraints: str = ""
    teachingStyle: str = ""
    assessment: str = ""
    structurePreferences: str = ""


class CurriculumIntakeState(StrictModel):
    readiness: Literal["gathering", "ready"]
    summary: str
    missingInformation: list[str] = Field(default_factory=list)
    capturedRequirements: CurriculumCapturedRequirements


class CurriculumIntakeArtifact(StrictModel):
    assistantMessage: str
    state: CurriculumIntakeState


class CurriculumPacingExpectations(StrictModel):
    totalWeeks: int | None = None
    sessionsPerWeek: int | None = None
    sessionMinutes: int | None = None
    totalSessionsLowerBound: int | None = None
    totalSessionsUpperBound: int | None = None


class CurriculumDraftSummary(StrictModel):
    title: str
    description: str
    subjects: list[str] = Field(default_factory=list)
    gradeLevels: list[str] = Field(default_factory=list)
    academicYear: str | None = None
    summary: str
    teachingApproach: str
    successSignals: list[str] = Field(default_factory=list)
    parentNotes: list[str] = Field(default_factory=list)
    rationale: list[str] = Field(default_factory=list)


class CurriculumPacing(StrictModel):
    totalWeeks: int | None = None
    sessionsPerWeek: int | None = None
    sessionMinutes: int | None = None
    totalSessions: int | None = None
    coverageStrategy: str
    coverageNotes: list[str] = Field(default_factory=list)


class CurriculumLesson(StrictModel):
    title: str
    description: str
    subject: str | None = None
    estimatedMinutes: int | None = None
    materials: list[str] = Field(default_factory=list)
    objectives: list[str] = Field(default_factory=list)
    linkedSkillTitles: list[str] = Field(default_factory=list)


class CurriculumUnit(StrictModel):
    title: str
    description: str
    estimatedWeeks: int | None = None
    estimatedSessions: int | None = None
    lessons: list[CurriculumLesson] = Field(default_factory=list)


class CurriculumArtifact(StrictModel):
    source: CurriculumDraftSummary
    intakeSummary: str
    pacing: CurriculumPacing
    document: dict[str, Any]
    units: list[CurriculumUnit] = Field(default_factory=list)
    progression: ProgressionArtifact | None = None


class CurriculumGenerationRequest(StrictModel):
    learnerName: str
    messages: list[CurriculumChatMessage] = Field(default_factory=list)
    requirementHints: CurriculumCapturedRequirements | None = None
    pacingExpectations: CurriculumPacingExpectations | None = None
    granularityGuidance: list[str] = Field(default_factory=list)
    correctionNotes: list[str] = Field(default_factory=list)


class CurriculumRevisionRequest(StrictModel):
    learnerName: str
    currentCurriculum: dict[str, Any]
    currentRequest: str | None = None
    messages: list[CurriculumChatMessage] = Field(default_factory=list)
    correctionNotes: list[str] = Field(default_factory=list)


class CurriculumRevisionTurn(StrictModel):
    assistantMessage: str
    action: Literal["clarify", "apply"]
    changeSummary: list[str] = Field(default_factory=list)
    artifact: CurriculumArtifact | None = None


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
