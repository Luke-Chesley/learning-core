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
    SourcePlanningConstraints,
)

CurriculumScale = Literal["micro", "week", "module", "course", "reference_source"]
CurriculumPlanningModel = Literal[
    "content_map",
    "session_sequence",
    "source_sequence",
    "single_lesson",
    "reference_map",
]
ContentAnchorGrounding = Literal["source_grounded", "parent_request", "model_suggested"]


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
    totalWeeks: int = Field(gt=0, le=104)
    sessionsPerWeek: int = Field(gt=0, le=14)
    sessionMinutes: int = Field(gt=0, le=360)
    totalSessions: int = Field(gt=0, le=500)
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
    description: str | None = None
    contentAnchorIds: list[str] = Field(default_factory=list, max_length=24)
    practiceCue: str | None = None
    assessmentCue: str | None = None

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


class SourceReference(StrictModel):
    label: str
    locator: str | None = None
    description: str | None = None


class ContentAnchor(StrictModel):
    anchorId: str
    title: str
    summary: str
    details: list[str] = Field(default_factory=list, max_length=12)
    sourceRefs: list[SourceReference] = Field(default_factory=list, max_length=12)
    grounding: ContentAnchorGrounding = "source_grounded"


class TeachableItem(StrictModel):
    itemId: str
    unitRef: str
    title: str
    focusQuestion: str
    contentAnchorIds: list[str] = Field(min_length=1, max_length=16)
    namedAnchors: list[str] = Field(min_length=1, max_length=24)
    vocabulary: list[str] = Field(default_factory=list, max_length=24)
    learnerOutcome: str
    assessmentCue: str
    misconceptions: list[str] = Field(default_factory=list, max_length=10)
    parentNotes: list[str] = Field(default_factory=list, max_length=10)
    skillIds: list[str] = Field(min_length=1, max_length=24)
    estimatedSessions: int | None = Field(default=None, gt=0, le=40)
    sourceRefs: list[SourceReference] = Field(default_factory=list, max_length=12)


class DeliverySequenceItem(StrictModel):
    sequenceId: str
    position: int = Field(gt=0, le=500)
    label: str
    title: str
    sessionFocus: str
    teachableItemId: str
    contentAnchorIds: list[str] = Field(default_factory=list, max_length=16)
    skillIds: list[str] = Field(min_length=1, max_length=24)
    estimatedMinutes: int | None = Field(default=None, gt=0, le=360)
    projectMilestone: str | None = None
    evidenceToSave: list[str] = Field(default_factory=list, max_length=8)
    reviewOf: list[str] = Field(default_factory=list, max_length=8)


class ProjectMilestone(StrictModel):
    title: str
    sessionPositions: list[int] = Field(default_factory=list, max_length=20)
    description: str
    evidenceToSave: list[str] = Field(default_factory=list, max_length=8)


class ProjectArc(StrictModel):
    goal: str
    milestones: list[ProjectMilestone] = Field(default_factory=list, max_length=12)
    presentationOptions: list[str] = Field(default_factory=list, max_length=8)
    evidenceToSave: list[str] = Field(default_factory=list, max_length=8)


class SourceCoverageItem(StrictModel):
    sourceRef: str
    coveredByItemIds: list[str] = Field(default_factory=list, max_length=40)
    notes: str | None = None


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
    planningModel: CurriculumPlanningModel = "content_map"
    skills: list[CurriculumSkill] = Field(min_length=1, max_length=400)
    units: list[CurriculumUnit] = Field(min_length=1, max_length=20)
    contentAnchors: list[ContentAnchor] = Field(min_length=1, max_length=600)
    teachableItems: list[TeachableItem] = Field(min_length=1, max_length=500)
    deliverySequence: list[DeliverySequenceItem] = Field(default_factory=list, max_length=500)
    projectArc: ProjectArc | None = None
    sourceCoverage: list[SourceCoverageItem] = Field(default_factory=list, max_length=120)

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

        anchor_ids = [anchor.anchorId for anchor in self.contentAnchors]
        if len(set(anchor_ids)) != len(anchor_ids):
            raise ValueError("CurriculumArtifact requires unique contentAnchors[].anchorId values.")

        known_anchor_ids = set(anchor_ids)
        for skill in self.skills:
            missing_anchor_ids = [
                anchor_id
                for anchor_id in skill.contentAnchorIds
                if anchor_id not in known_anchor_ids
            ]
            if missing_anchor_ids:
                raise ValueError(
                    f'CurriculumArtifact skill "{skill.title}" references unknown contentAnchorIds: '
                    + ", ".join(sorted(missing_anchor_ids))
                )

        teachable_item_ids = [item.itemId for item in self.teachableItems]
        if len(set(teachable_item_ids)) != len(teachable_item_ids):
            raise ValueError("CurriculumArtifact requires unique teachableItems[].itemId values.")

        unit_ref_set = set(unit_refs)
        skill_ids_with_teachable_items: set[str] = set()
        for item in self.teachableItems:
            if item.unitRef not in unit_ref_set:
                raise ValueError(
                    f'CurriculumArtifact teachable item "{item.title}" references unknown unitRef "{item.unitRef}".'
                )

            missing_skill_ids = [skill_id for skill_id in item.skillIds if skill_id not in known_skill_ids]
            if missing_skill_ids:
                raise ValueError(
                    f'CurriculumArtifact teachable item "{item.title}" references unknown skillIds: '
                    + ", ".join(sorted(missing_skill_ids))
                )
            skill_ids_with_teachable_items.update(item.skillIds)

            missing_anchor_ids = [
                anchor_id
                for anchor_id in item.contentAnchorIds
                if anchor_id not in known_anchor_ids
            ]
            if missing_anchor_ids:
                raise ValueError(
                    f'CurriculumArtifact teachable item "{item.title}" references unknown contentAnchorIds: '
                    + ", ".join(sorted(missing_anchor_ids))
                )

        skills_without_content = [
            skill.skillId
            for skill in self.skills
            if not skill.contentAnchorIds and skill.skillId not in skill_ids_with_teachable_items
        ]
        if skills_without_content:
            raise ValueError(
                "Every skill must be grounded by contentAnchorIds or a teachable item. Missing: "
                + ", ".join(sorted(skills_without_content))
            )

        item_by_id = {item.itemId: item for item in self.teachableItems}
        sequence_ids = [item.sequenceId for item in self.deliverySequence]
        if len(set(sequence_ids)) != len(sequence_ids):
            raise ValueError("CurriculumArtifact requires unique deliverySequence[].sequenceId values.")

        seen_positions: set[int] = set()
        seen_sequence_teachable_item_ids: set[str] = set()
        seen_sequence_primary_skill_ids: set[str] = set()
        for sequence_item in self.deliverySequence:
            if sequence_item.position in seen_positions:
                raise ValueError("CurriculumArtifact requires unique deliverySequence[].position values.")
            seen_positions.add(sequence_item.position)

            teachable_item = item_by_id.get(sequence_item.teachableItemId)
            if not teachable_item:
                raise ValueError(
                    f'CurriculumArtifact delivery item "{sequence_item.title}" references unknown teachableItemId '
                    f'"{sequence_item.teachableItemId}".'
                )
            if self.planningModel == "session_sequence":
                if sequence_item.teachableItemId in seen_sequence_teachable_item_ids:
                    raise ValueError(
                        'planningModel "session_sequence" requires each deliverySequence item to use a unique teachableItemId.'
                    )
                seen_sequence_teachable_item_ids.add(sequence_item.teachableItemId)

                primary_skill_id = sequence_item.skillIds[0]
                if primary_skill_id in seen_sequence_primary_skill_ids:
                    raise ValueError(
                        'planningModel "session_sequence" requires each deliverySequence item to use a unique primary skillId.'
                    )
                seen_sequence_primary_skill_ids.add(primary_skill_id)

            missing_skill_ids = [
                skill_id for skill_id in sequence_item.skillIds if skill_id not in known_skill_ids
            ]
            if missing_skill_ids:
                raise ValueError(
                    f'CurriculumArtifact delivery item "{sequence_item.title}" references unknown skillIds: '
                    + ", ".join(sorted(missing_skill_ids))
                )

            if not set(sequence_item.skillIds).issubset(set(teachable_item.skillIds)):
                raise ValueError(
                    f'CurriculumArtifact delivery item "{sequence_item.title}" must use skillIds from its teachable item.'
                )

            if not sequence_item.contentAnchorIds:
                sequence_item.contentAnchorIds = list(teachable_item.contentAnchorIds)

            missing_anchor_ids = [
                anchor_id
                for anchor_id in sequence_item.contentAnchorIds
                if anchor_id not in known_anchor_ids
            ]
            if missing_anchor_ids:
                raise ValueError(
                    f'CurriculumArtifact delivery item "{sequence_item.title}" references unknown contentAnchorIds: '
                    + ", ".join(sorted(missing_anchor_ids))
                )

        if self.deliverySequence:
            expected_positions = list(range(1, len(self.deliverySequence) + 1))
            actual_positions = sorted(seen_positions)
            if actual_positions != expected_positions:
                raise ValueError(
                    "CurriculumArtifact deliverySequence positions must be contiguous and start at 1."
                )

        if self.planningModel == "session_sequence":
            if not self.deliverySequence:
                raise ValueError('planningModel "session_sequence" requires deliverySequence.')
            if self.pacing.totalSessions is not None and self.pacing.totalSessions <= 80:
                if len(self.deliverySequence) != self.pacing.totalSessions:
                    raise ValueError(
                        'planningModel "session_sequence" requires one deliverySequence item per total session.'
                    )

        if self.planningModel == "single_lesson" and len(self.deliverySequence) > 1:
            raise ValueError('planningModel "single_lesson" may include at most one deliverySequence item.')

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
    planningConstraints: SourcePlanningConstraints | None = None

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
