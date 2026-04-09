from __future__ import annotations

from typing import Any, Literal

from pydantic import ConfigDict, Field, field_validator

from learning_core.contracts.base import StrictModel
from learning_core.contracts.lesson_draft import StructuredLessonDraft


INTERACTIVE_COMPONENT_TYPES = {
    "short_answer",
    "text_response",
    "rich_text_response",
    "single_select",
    "multi_select",
    "rating",
    "confidence_check",
    "checklist",
    "ordered_sequence",
    "matching_pairs",
    "categorization",
    "sort_into_groups",
    "label_map",
    "hotspot_select",
    "build_steps",
    "drag_arrange",
    "reflection_prompt",
    "rubric_self_check",
    "file_upload",
    "image_capture",
    "audio_capture",
    "observation_record",
    "teacher_checkoff",
    "compare_and_explain",
    "choose_next_step",
    "construction_space",
}


class ActivityComponent(StrictModel):
    id: str
    type: str
    model_config = ConfigDict(extra="allow")


class CompletionRules(StrictModel):
    strategy: Literal[
        "all_interactive_components",
        "minimum_components",
        "any_submission",
        "teacher_approval",
    ] = "all_interactive_components"
    minimumComponents: int | None = None
    incompleteMessage: str | None = None


class EvidenceSchema(StrictModel):
    captureKinds: list[str] = Field(default_factory=list)
    requiresReview: bool
    autoScorable: bool
    reviewerNotes: str | None = None


class ScoringModel(StrictModel):
    mode: Literal[
        "correctness_based",
        "completion_based",
        "rubric_based",
        "teacher_observed",
        "confidence_report",
        "evidence_collected",
    ]
    masteryThreshold: float | None = None
    reviewThreshold: float | None = None
    notes: str | None = None


class AdaptationRules(StrictModel):
    hintStrategy: Literal["on_request", "always", "after_wrong_attempt"] = "on_request"
    allowSkip: bool = False
    allowRetry: bool = False
    maxRetries: int | None = None


class TeacherSupport(StrictModel):
    setupNotes: str | None = None
    discussionQuestions: list[str] = Field(default_factory=list)
    masteryIndicators: list[str] = Field(default_factory=list)
    commonMistakes: str | None = None
    extensionIdeas: str | None = None


class OfflineMode(StrictModel):
    offlineTaskDescription: str
    materials: list[str] = Field(default_factory=list)
    evidenceCaptureInstruction: str | None = None


class ActivityArtifact(StrictModel):
    schemaVersion: Literal["2"]
    title: str
    purpose: str
    activityKind: str
    linkedObjectiveIds: list[str] = Field(default_factory=list)
    linkedSkillTitles: list[str] = Field(default_factory=list)
    estimatedMinutes: int
    interactionMode: Literal["digital", "offline", "hybrid"]
    components: list[ActivityComponent]
    completionRules: CompletionRules
    evidenceSchema: EvidenceSchema
    scoringModel: ScoringModel
    adaptationRules: AdaptationRules | None = None
    teacherSupport: TeacherSupport | None = None
    offlineMode: OfflineMode | None = None
    templateHint: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("components")
    @classmethod
    def validate_components(cls, value: list[ActivityComponent]) -> list[ActivityComponent]:
        if not value:
            raise ValueError("Activity artifact must include at least one component.")
        ids = [component.id for component in value]
        if len(ids) != len(set(ids)):
            raise ValueError("Activity artifact component ids must be unique.")
        if not any(component.type in INTERACTIVE_COMPONENT_TYPES for component in value):
            raise ValueError("Activity artifact must include at least one interactive component.")
        return value


class ActivityGenerationInput(StrictModel):
    learner_name: str
    learner_grade_level: str | None = None
    workflow_mode: str | None = None
    subject: str | None = None
    source_title: str | None = None
    lesson_session_id: str | None = None
    lead_plan_item_id: str | None = None
    plan_item_ids: list[str] = Field(default_factory=list)
    linked_skill_titles: list[str] = Field(default_factory=list)
    linked_objective_ids: list[str] = Field(default_factory=list)
    standard_ids: list[str] = Field(default_factory=list)
    lesson_draft: StructuredLessonDraft
