from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import Field, model_validator

from learning_core.contracts.base import StrictModel
from learning_core.contracts.progression import ProgressionArtifact
from learning_core.contracts.source_interpret import (
    RequestedIntakeRoute,
    SourceContinuationMode,
    SourceDeliveryPattern,
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
    unitRef: str
    lessonRef: str
    lessonType: Literal[
        "task",
        "skill_support",
        "concept",
        "setup",
        "reflection",
        "assessment",
    ]
    title: str
    description: str
    subject: str | None = None
    estimatedMinutes: int | None = None
    materials: list[str] = Field(default_factory=list)
    objectives: list[str] = Field(default_factory=list)
    linkedSkillRefs: list[str] = Field(default_factory=list)


class CurriculumUnit(StrictModel):
    unitRef: str
    title: str
    description: str
    estimatedWeeks: int | None = None
    estimatedSessions: int | None = None
    lessons: list[CurriculumLesson] = Field(default_factory=list)


class CurriculumLaunchPlan(StrictModel):
    recommendedHorizon: SourceInterpretationHorizon
    openingLessonRefs: list[str] = Field(default_factory=list)
    openingSkillRefs: list[str] = Field(default_factory=list)
    scopeSummary: str
    initialSliceUsed: bool
    initialSliceLabel: str | None = None
    entryStrategy: SourceEntryStrategy | None = None
    entryLabel: str | None = None
    continuationMode: SourceContinuationMode | None = None

    @model_validator(mode="after")
    def validate_opening_refs(self) -> "CurriculumLaunchPlan":
        if not self.openingLessonRefs:
            raise ValueError("launchPlan requires at least one openingLessonRef.")
        return self


def normalize_ref_segment(value: str) -> str:
    normalized = value.strip().lower()
    normalized = normalized.replace("’", "").replace("'", "")
    normalized = re.sub(r"[^a-z0-9]+", "-", normalized)
    normalized = re.sub(r"-{2,}", "-", normalized)
    return normalized.strip("-")


def normalize_skill_ref(skill_ref: str) -> str:
    prefix = "skill:"
    body = skill_ref[len(prefix) :] if skill_ref.startswith(prefix) else skill_ref
    normalized_parts = [
        normalize_ref_segment(part)
        for part in body.split("/")
        if normalize_ref_segment(part)
    ]
    return prefix + "/".join(normalized_parts)


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


def build_document_skill_ref_aliases(document: dict[str, Any]) -> tuple[dict[str, str], set[str]]:
    aliases: dict[str, str] = {}
    ambiguous: set[str] = set()
    leaf_aliases: dict[str, str] = {}
    ambiguous_leaf_aliases: set[str] = set()
    for canonical_ref, path, title in iter_document_skill_entries(document):
        normalized_ref = normalize_skill_ref(canonical_ref)
        existing = aliases.get(normalized_ref)
        if existing and existing != canonical_ref:
            ambiguous.add(normalized_ref)
            aliases.pop(normalized_ref, None)
        elif normalized_ref not in ambiguous:
            aliases[normalized_ref] = canonical_ref
        leaf_alias = normalize_ref_segment(title or path[-1])
        existing_leaf = leaf_aliases.get(leaf_alias)
        if existing_leaf and existing_leaf != canonical_ref:
            ambiguous_leaf_aliases.add(leaf_alias)
            leaf_aliases.pop(leaf_alias, None)
        elif leaf_alias not in ambiguous_leaf_aliases:
            leaf_aliases[leaf_alias] = canonical_ref
    for leaf_alias, canonical_ref in leaf_aliases.items():
        if leaf_alias not in ambiguous_leaf_aliases and leaf_alias not in aliases:
            aliases[leaf_alias] = canonical_ref
    return aliases, ambiguous


def resolve_document_skill_ref(document: dict[str, Any], skill_ref: str) -> str | None:
    aliases, ambiguous = build_document_skill_ref_aliases(document)
    normalized_ref = normalize_skill_ref(skill_ref)
    if normalized_ref in ambiguous:
        return None
    return aliases.get(normalized_ref)


class CurriculumArtifact(StrictModel):
    source: CurriculumDraftSummary
    intakeSummary: str
    pacing: CurriculumPacing
    document: dict[str, Any]
    units: list[CurriculumUnit] = Field(default_factory=list)
    launchPlan: CurriculumLaunchPlan
    progression: ProgressionArtifact | None = None

    @model_validator(mode="after")
    def validate_refs(self) -> "CurriculumArtifact":
        unit_refs = {unit.unitRef for unit in self.units}
        if len(unit_refs) != len(self.units):
            raise ValueError("CurriculumArtifact requires unique unitRef values.")

        lesson_refs: set[str] = set()
        document_skill_aliases, ambiguous_skill_refs = build_document_skill_ref_aliases(self.document)

        def canonicalize_skill_refs(skill_refs: list[str]) -> tuple[list[str], list[str]]:
            canonicalized: list[str] = []
            missing: list[str] = []
            seen: set[str] = set()
            for skill_ref in skill_refs:
                normalized_ref = normalize_skill_ref(skill_ref)
                leaf_ref = normalize_ref_segment(skill_ref.split("/")[-1] if "/" in skill_ref else skill_ref)
                if normalized_ref in ambiguous_skill_refs or leaf_ref in ambiguous_skill_refs:
                    missing.append(skill_ref)
                    continue
                canonical_ref = document_skill_aliases.get(normalized_ref) or document_skill_aliases.get(leaf_ref)
                if not canonical_ref:
                    missing.append(skill_ref)
                    continue
                if canonical_ref not in seen:
                    canonicalized.append(canonical_ref)
                    seen.add(canonical_ref)
            return canonicalized, missing

        for unit in self.units:
            for lesson in unit.lessons:
                if lesson.unitRef != unit.unitRef:
                    raise ValueError(
                        f'Lesson "{lesson.title}" unitRef must match parent unitRef.'
                    )
                if lesson.lessonRef in lesson_refs:
                    raise ValueError("CurriculumArtifact requires unique lessonRef values.")
                lesson_refs.add(lesson.lessonRef)
                canonical_linked_refs, missing_skill_refs = canonicalize_skill_refs(lesson.linkedSkillRefs)
                lesson.linkedSkillRefs = canonical_linked_refs
                if missing_skill_refs:
                    raise ValueError(
                        "CurriculumArtifact lesson contains unresolved linkedSkillRefs: "
                        + ", ".join(sorted(missing_skill_refs))
                    )

        missing_opening_lessons = [
            lesson_ref
            for lesson_ref in self.launchPlan.openingLessonRefs
            if lesson_ref not in lesson_refs
        ]
        if missing_opening_lessons:
            raise ValueError(
                "CurriculumArtifact launchPlan contains unresolved openingLessonRefs: "
                + ", ".join(sorted(missing_opening_lessons))
            )

        canonical_opening_skill_refs, missing_opening_skills = canonicalize_skill_refs(
            self.launchPlan.openingSkillRefs
        )
        self.launchPlan.openingSkillRefs = canonical_opening_skill_refs
        if missing_opening_skills:
            raise ValueError(
                "CurriculumArtifact launchPlan contains unresolved openingSkillRefs: "
                + ", ".join(sorted(missing_opening_skills))
            )

        return self


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
    deliveryPattern: SourceDeliveryPattern | None = None
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
                "deliveryPattern": self.deliveryPattern,
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
