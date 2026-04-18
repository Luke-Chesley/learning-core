from __future__ import annotations

from typing import Any, Literal

from pydantic import Field, model_validator

from learning_core.contracts.base import StrictModel
from learning_core.contracts.progression import ProgressionArtifact
from learning_core.contracts.source_interpret import (
    RequestedIntakeRoute,
    SourceContinuationMode,
    SourceEntryStrategy,
    SourceInputFile,
    SourceKind,
    SourcePackageContext,
    SourceInterpretationHorizon,
)


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


class CurriculumLaunchPlan(StrictModel):
    recommendedHorizon: SourceInterpretationHorizon
    openingLessonCount: int = Field(ge=1)
    scopeSummary: str
    initialSliceUsed: bool
    initialSliceLabel: str | None = None
    entryStrategy: SourceEntryStrategy | None = None
    entryLabel: str | None = None
    continuationMode: SourceContinuationMode | None = None


class CurriculumArtifact(StrictModel):
    source: CurriculumDraftSummary
    intakeSummary: str
    pacing: CurriculumPacing
    document: dict[str, Any]
    units: list[CurriculumUnit] = Field(default_factory=list)
    launchPlan: CurriculumLaunchPlan
    progression: ProgressionArtifact | None = None


class CurriculumIntakeRequest(StrictModel):
    learnerName: str
    messages: list[CurriculumChatMessage] = Field(default_factory=list)
    requirementHints: CurriculumCapturedRequirements | None = None


class CurriculumGenerationRequest(StrictModel):
    learnerName: str
    titleCandidate: str | None = None
    requestMode: Literal["source_entry", "conversation_intake"]
    requestedRoute: RequestedIntakeRoute | None = None
    routedRoute: RequestedIntakeRoute | None = None
    sourceKind: SourceKind | None = None
    entryStrategy: SourceEntryStrategy | None = None
    entryLabel: str | None = None
    continuationMode: SourceContinuationMode | None = None
    recommendedHorizon: SourceInterpretationHorizon | None = None
    sourceText: str | None = None
    sourcePackages: list[SourcePackageContext] | None = None
    sourceFiles: list[SourceInputFile] | None = None
    detectedChunks: list[str] | None = None
    assumptions: list[str] | None = None
    messages: list[CurriculumChatMessage] | None = None
    requirementHints: CurriculumCapturedRequirements | None = None
    pacingExpectations: CurriculumPacingExpectations | None = None
    granularityGuidance: list[str] | None = None
    correctionNotes: list[str] | None = None

    @model_validator(mode="after")
    def validate_mode_fields(self) -> "CurriculumGenerationRequest":
        if self.requestMode == "source_entry":
            required_fields = {
                "requestedRoute": self.requestedRoute,
                "routedRoute": self.routedRoute,
                "sourceKind": self.sourceKind,
                "entryStrategy": self.entryStrategy,
                "continuationMode": self.continuationMode,
                "recommendedHorizon": self.recommendedHorizon,
                "sourceText": self.sourceText,
                "sourcePackages": self.sourcePackages,
                "sourceFiles": self.sourceFiles,
                "detectedChunks": self.detectedChunks,
                "assumptions": self.assumptions,
            }
            missing = [name for name, value in required_fields.items() if value is None]
            if missing:
                raise ValueError(
                    "source_entry requests require: " + ", ".join(sorted(missing))
                )
            if not self.sourceText or not self.sourceText.strip():
                raise ValueError("source_entry requests require non-empty sourceText.")
            forbidden_fields = {
                "messages": self.messages,
                "requirementHints": self.requirementHints,
                "pacingExpectations": self.pacingExpectations,
                "granularityGuidance": self.granularityGuidance,
                "correctionNotes": self.correctionNotes,
            }
            populated_forbidden = [
                name for name, value in forbidden_fields.items() if value is not None
            ]
            if populated_forbidden:
                raise ValueError(
                    "source_entry requests do not allow: "
                    + ", ".join(sorted(populated_forbidden))
                )
            return self

        required_conversation_fields = {
            "messages": self.messages,
        }
        missing = [name for name, value in required_conversation_fields.items() if value is None]
        if missing:
            raise ValueError(
                "conversation_intake requests require: " + ", ".join(sorted(missing))
            )
        if not self.messages:
            raise ValueError("conversation_intake requests require at least one message.")
        forbidden_fields = {
            "sourceKind": self.sourceKind,
            "entryStrategy": self.entryStrategy,
            "entryLabel": self.entryLabel,
            "continuationMode": self.continuationMode,
            "recommendedHorizon": self.recommendedHorizon,
            "sourceText": self.sourceText,
            "sourcePackages": self.sourcePackages,
            "sourceFiles": self.sourceFiles,
            "detectedChunks": self.detectedChunks,
            "assumptions": self.assumptions,
        }
        populated_forbidden = [
            name for name, value in forbidden_fields.items() if value is not None
        ]
        if populated_forbidden:
            raise ValueError(
                "conversation_intake requests do not allow: "
                + ", ".join(sorted(populated_forbidden))
            )
        return self


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
