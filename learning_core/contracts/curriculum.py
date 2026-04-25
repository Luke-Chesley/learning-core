from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import Field, model_validator

from learning_core.contracts.base import StrictModel
from learning_core.contracts.source_interpret import (
    RequestedIntakeRoute,
    SourceContinuationMode,
    SourceDeliveryPattern,
    SourceEntryStrategy,
    SourceInputFile,
    SourceInterpretationHorizon,
    SourceKind,
    SourcePackageContext,
)

CurriculumScale = Literal["micro", "week", "module", "course", "reference_source"]


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


class CurriculumIntakeRequest(StrictModel):
    learnerName: str
    messages: list[CurriculumChatMessage] = Field(default_factory=list)
    requirementHints: dict[str, Any] | None = None


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
    totalWeeks: int | None = Field(default=None, gt=0, le=52)
    sessionsPerWeek: int | None = Field(default=None, gt=0, le=14)
    sessionMinutes: int | None = Field(default=None, gt=0, le=360)
    totalSessions: int | None = Field(default=None, gt=0, le=500)
    coverageStrategy: str
    coverageNotes: list[str] = Field(default_factory=list)


def normalize_ref_segment(value: str) -> str:
    normalized = value.strip().lower()
    normalized = re.sub(r"[^a-z0-9]+", "-", normalized)
    normalized = re.sub(r"-{2,}", "-", normalized)
    return normalized.strip("-")


def canonical_skill_ref_from_titles(
    domain_title: str,
    strand_title: str,
    goal_group_title: str,
    title: str,
) -> str:
    return "skill:" + "/".join(
        normalize_ref_segment(segment)
        for segment in (domain_title, strand_title, goal_group_title, title)
    )


class CurriculumSkill(StrictModel):
    skillId: str
    domainTitle: str | None = None
    strandTitle: str | None = None
    goalGroupTitle: str | None = None
    title: str

    def canonical_skill_ref(self) -> str:
        return canonical_skill_ref_from_titles(
            self.domainTitle or "Curriculum",
            self.strandTitle or "Core Sequence",
            self.goalGroupTitle or "Focus Skills",
            self.title,
        )


class CurriculumUnit(StrictModel):
    unitRef: str
    title: str
    description: str
    estimatedWeeks: int | None = Field(default=None, gt=0, le=52)
    estimatedSessions: int | None = Field(default=None, gt=0, le=160)
    skillIds: list[str] = Field(min_length=1, max_length=64)


def iter_document_skill_entries(
    node: dict[str, Any],
    path: list[str] | None = None,
) -> list[tuple[str, list[str], str]]:
    entries: list[tuple[str, list[str], str]] = []
    current_path = path or []
    for title, value in node.items():
        next_path = [*current_path, title]
        if isinstance(value, str):
            canonical_ref = "skill:" + "/".join(
                normalize_ref_segment(segment) for segment in next_path
            )
            entries.append((canonical_ref, next_path, title))
            continue
        if isinstance(value, list):
            for item in value:
                if isinstance(item, str):
                    item_path = [*next_path, item]
                    canonical_ref = "skill:" + "/".join(
                        normalize_ref_segment(segment) for segment in item_path
                    )
                    entries.append((canonical_ref, item_path, item))
            continue
        if isinstance(value, dict):
            entries.extend(iter_document_skill_entries(value, next_path))
    return entries


def iter_curriculum_skill_entries(
    skills: list[CurriculumSkill],
) -> list[tuple[str, list[str], str]]:
    return [
        (
            skill.canonical_skill_ref(),
            [
                skill.domainTitle or "Curriculum",
                skill.strandTitle or "Core Sequence",
                skill.goalGroupTitle or "Focus Skills",
                skill.title,
            ],
            skill.title,
        )
        for skill in skills
    ]


class CurriculumArtifact(StrictModel):
    source: CurriculumDraftSummary
    intakeSummary: str
    pacing: CurriculumPacing
    curriculumScale: CurriculumScale | None = None
    skills: list[CurriculumSkill] = Field(min_length=1, max_length=400)
    units: list[CurriculumUnit] = Field(min_length=1, max_length=20)

    @model_validator(mode="after")
    def validate_refs(self) -> "CurriculumArtifact":
        skill_ids = [skill.skillId for skill in self.skills]
        if len(set(skill_ids)) != len(self.skills):
            raise ValueError("CurriculumArtifact requires unique skillId values.")

        canonical_skill_refs = [skill.canonical_skill_ref() for skill in self.skills]
        if len(set(canonical_skill_refs)) != len(canonical_skill_refs):
            raise ValueError("CurriculumArtifact contains duplicate skill paths.")

        unit_refs = {unit.unitRef for unit in self.units}
        if len(unit_refs) != len(self.units):
            raise ValueError("CurriculumArtifact requires unique unitRef values.")

        known_skill_ids = set(skill_ids)
        for unit in self.units:
            deduped_skill_ids: list[str] = []
            seen: set[str] = set()
            missing_skill_ids: list[str] = []
            for skill_id in unit.skillIds:
                if skill_id not in known_skill_ids:
                    missing_skill_ids.append(skill_id)
                    continue
                if skill_id in seen:
                    continue
                seen.add(skill_id)
                deduped_skill_ids.append(skill_id)
            unit.skillIds = deduped_skill_ids
            if missing_skill_ids:
                raise ValueError(
                    "CurriculumArtifact unit contains unknown skillIds: "
                    + ", ".join(sorted(missing_skill_ids))
                )
            if not unit.skillIds:
                raise ValueError(f'CurriculumArtifact unit "{unit.title}" requires at least one skillId.')

        return self


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
    deliveryPattern: SourceDeliveryPattern | None = None
    recommendedHorizon: SourceInterpretationHorizon | None = None
    sourceText: str | None = None
    sourcePackages: list[SourcePackageContext] = Field(default_factory=list)
    sourceFiles: list[SourceInputFile] = Field(default_factory=list)
    detectedChunks: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)

    messages: list[CurriculumChatMessage] = Field(default_factory=list)
    requirementHints: dict[str, Any] | None = None
    pacingExpectations: CurriculumPacingExpectations | None = None
    granularityGuidance: list[str] = Field(default_factory=list)
    correctionNotes: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_request_mode(self) -> "CurriculumGenerationRequest":
        if self.requestMode == "source_entry":
            required_source_fields = {
                "requestedRoute": self.requestedRoute,
                "routedRoute": self.routedRoute,
                "sourceKind": self.sourceKind,
                "entryStrategy": self.entryStrategy,
                "continuationMode": self.continuationMode,
                "deliveryPattern": self.deliveryPattern,
                "recommendedHorizon": self.recommendedHorizon,
                "sourceText": self.sourceText,
            }
            missing = [name for name, value in required_source_fields.items() if value in (None, "")]
            if missing:
                raise ValueError(
                    "source_entry curriculum generation requires: " + ", ".join(sorted(missing))
                )
        else:
            if not self.messages:
                raise ValueError("conversation_intake curriculum generation requires messages.")
            forbidden_source_fields = {
                "requestedRoute": self.requestedRoute,
                "routedRoute": self.routedRoute,
                "sourceKind": self.sourceKind,
                "entryStrategy": self.entryStrategy,
                "entryLabel": self.entryLabel,
                "continuationMode": self.continuationMode,
                "deliveryPattern": self.deliveryPattern,
                "recommendedHorizon": self.recommendedHorizon,
                "sourceText": self.sourceText,
                "sourcePackages": self.sourcePackages,
                "sourceFiles": self.sourceFiles,
                "detectedChunks": self.detectedChunks,
                "assumptions": self.assumptions,
            }
            present = [
                name
                for name, value in forbidden_source_fields.items()
                if value not in (None, "") and value != []
            ]
            if present:
                raise ValueError(
                    "conversation_intake curriculum generation does not accept source-entry fields: "
                    + ", ".join(sorted(present))
                )
        return self


class CurriculumRevisionRequest(StrictModel):
    learnerName: str
    currentCurriculum: dict[str, Any] | None = None
    currentRequest: str | None = None
    messages: list[CurriculumChatMessage] = Field(default_factory=list)
    correctionNotes: list[str] = Field(default_factory=list)


class CurriculumRevisionTurn(StrictModel):
    assistantMessage: str
    action: Literal["clarify", "apply"]
    changeSummary: list[str] = Field(default_factory=list)
    artifact: CurriculumArtifact | None = None

    @model_validator(mode="after")
    def validate_action_payload(self) -> "CurriculumRevisionTurn":
        if self.action == "apply" and self.artifact is None:
            raise ValueError('artifact is required when action is "apply".')
        if self.action == "clarify" and self.artifact is not None:
            raise ValueError('artifact must be omitted when action is "clarify".')
        return self
