from __future__ import annotations
from typing import Annotated, Literal

from pydantic import AliasChoices, Field, field_validator, model_validator

from learning_core.contracts.base import StrictModel
from learning_core.contracts.lesson_draft import StructuredLessonDraft
from learning_core.contracts.widgets import InteractiveWidgetPayload, widget_accepts_input


ActivityKind = Literal[
    "guided_practice",
    "retrieval",
    "demonstration",
    "simulation",
    "discussion_capture",
    "reflection",
    "performance_task",
    "project_step",
    "observation",
    "assessment_check",
    "collaborative",
    "offline_real_world",
]

EvidenceKind = Literal[
    "answer_response",
    "file_artifact",
    "image_artifact",
    "audio_artifact",
    "self_assessment",
    "teacher_observation",
    "teacher_checkoff",
    "completion_marker",
    "confidence_signal",
    "reflection_response",
    "rubric_score",
    "ordering_result",
    "matching_result",
    "categorization_result",
    "construction_product",
]

ScoringMode = Literal[
    "correctness_based",
    "completion_based",
    "rubric_based",
    "teacher_observed",
    "confidence_report",
    "evidence_collected",
]

ActivityTemplateHint = Literal[
    "exploratory",
    "practice_heavy",
    "demonstration_then_try",
    "evidence_capture",
    "reflection_first",
    "project_step",
]

InteractionMode = Literal["digital", "offline", "hybrid"]

ComponentType = Literal[
    "heading",
    "paragraph",
    "callout",
    "image",
    "divider",
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
    "interactive_widget",
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
]

INTERACTIVE_COMPONENT_TYPES: set[ComponentType] = {
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


class HeadingComponent(StrictModel):
    type: Literal["heading"]
    id: str
    level: int = Field(default=2, ge=1, le=4)
    text: str = Field(validation_alias=AliasChoices("text", "content"))


class ParagraphComponent(StrictModel):
    type: Literal["paragraph"]
    id: str
    text: str = Field(validation_alias=AliasChoices("text", "content"))
    markdown: str | None = None


class CalloutComponent(StrictModel):
    type: Literal["callout"]
    id: str
    variant: Literal["info", "tip", "warning", "note"] = Field(
        default="info", validation_alias=AliasChoices("variant", "style")
    )
    text: str = Field(validation_alias=AliasChoices("text", "content"))


class ImageComponent(StrictModel):
    type: Literal["image"]
    id: str
    src: str
    alt: str
    caption: str | None = None


class DividerComponent(StrictModel):
    type: Literal["divider"]
    id: str


class ShortAnswerComponent(StrictModel):
    type: Literal["short_answer"]
    id: str
    prompt: str
    placeholder: str | None = None
    hint: str | None = None
    expectedAnswer: str | None = None
    required: bool = True


class TextResponseComponent(StrictModel):
    type: Literal["text_response"]
    id: str
    prompt: str
    placeholder: str | None = None
    hint: str | None = None
    minWords: int | None = Field(default=None, gt=0)
    required: bool = True


class RichTextResponseComponent(StrictModel):
    type: Literal["rich_text_response"]
    id: str
    prompt: str
    hint: str | None = None
    required: bool = True


class SingleSelectChoice(StrictModel):
    id: str = Field(validation_alias=AliasChoices("id", "value"))
    text: str = Field(validation_alias=AliasChoices("text", "label"))
    correct: bool | None = None
    explanation: str | None = None


class SingleSelectComponent(StrictModel):
    type: Literal["single_select"]
    id: str
    prompt: str
    choices: list[SingleSelectChoice] = Field(min_length=2, validation_alias=AliasChoices("choices", "options"))
    immediateCorrectness: bool = False
    shuffleOptions: bool | None = None
    correctValue: str | None = None
    hint: str | None = None
    required: bool = True


class MultiSelectChoice(StrictModel):
    id: str = Field(validation_alias=AliasChoices("id", "value"))
    text: str = Field(validation_alias=AliasChoices("text", "label"))
    correct: bool | None = None


class MultiSelectComponent(StrictModel):
    type: Literal["multi_select"]
    id: str
    prompt: str
    choices: list[MultiSelectChoice] = Field(min_length=2, validation_alias=AliasChoices("choices", "options"))
    minSelections: int | None = Field(default=None, ge=0)
    maxSelections: int | None = Field(default=None, gt=0)
    hint: str | None = None
    required: bool = True


class RatingComponent(StrictModel):
    type: Literal["rating"]
    id: str
    prompt: str
    min: int = 1
    max: int = 5
    lowLabel: str | None = None
    highLabel: str | None = None
    required: bool = True


class ConfidenceCheckComponent(StrictModel):
    type: Literal["confidence_check"]
    id: str
    prompt: str = "How confident are you with this?"
    labels: list[str] = Field(
        default_factory=lambda: [
            "Not yet",
            "A little",
            "Getting there",
            "Pretty good",
            "Got it!",
        ],
        min_length=5,
        max_length=5,
    )
    required: bool = True


class ChecklistItem(StrictModel):
    id: str
    label: str
    description: str | None = None
    required: bool = True


class ChecklistComponent(StrictModel):
    type: Literal["checklist"]
    id: str
    prompt: str | None = None
    items: list[ChecklistItem] = Field(min_length=1)
    allowPartialSubmit: bool = False


class OrderedSequenceItem(StrictModel):
    id: str
    text: str
    correctIndex: int = Field(ge=0)


class OrderedSequenceComponent(StrictModel):
    type: Literal["ordered_sequence"]
    id: str
    prompt: str
    items: list[OrderedSequenceItem] = Field(min_length=2)
    hint: str | None = None


class MatchingPair(StrictModel):
    id: str
    left: str
    right: str
    leftImageUrl: str | None = None
    rightImageUrl: str | None = None


class MatchingPairsComponent(StrictModel):
    type: Literal["matching_pairs"]
    id: str
    prompt: str | None = None
    pairs: list[MatchingPair] = Field(min_length=2)
    hint: str | None = None


class CategorizationCategory(StrictModel):
    id: str
    label: str


class CategorizationItem(StrictModel):
    id: str
    text: str
    correctCategoryIds: list[str] = Field(min_length=1)


class CategorizationComponent(StrictModel):
    type: Literal["categorization"]
    id: str
    prompt: str
    categories: list[CategorizationCategory] = Field(min_length=2)
    items: list[CategorizationItem] = Field(min_length=2)
    hint: str | None = None


class SortIntoGroup(StrictModel):
    id: str
    label: str
    description: str | None = None


class SortIntoGroupItem(StrictModel):
    id: str
    text: str
    correctGroupId: str


class SortIntoGroupsComponent(StrictModel):
    type: Literal["sort_into_groups"]
    id: str
    prompt: str
    groups: list[SortIntoGroup] = Field(min_length=2)
    items: list[SortIntoGroupItem] = Field(min_length=2)
    hint: str | None = None


class LabelMapLabel(StrictModel):
    id: str
    x: float = Field(ge=0, le=100)
    y: float = Field(ge=0, le=100)
    correctText: str
    hint: str | None = None


class LabelMapComponent(StrictModel):
    type: Literal["label_map"]
    id: str
    prompt: str
    imageUrl: str
    imageAlt: str
    labels: list[LabelMapLabel] = Field(min_length=1)


class Hotspot(StrictModel):
    id: str
    x: float = Field(ge=0, le=100)
    y: float = Field(ge=0, le=100)
    radius: float = Field(default=5, gt=0)
    label: str
    correct: bool | None = None


class HotspotSelectComponent(StrictModel):
    type: Literal["hotspot_select"]
    id: str
    prompt: str
    imageUrl: str
    imageAlt: str
    hotspots: list[Hotspot] = Field(min_length=1)
    requiredSelections: int | None = Field(default=None, gt=0)
    hint: str | None = None


class BuildStep(StrictModel):
    id: str
    instruction: str
    hint: str | None = None
    expectedValue: str | None = None


class BuildStepsComponent(StrictModel):
    type: Literal["build_steps"]
    id: str
    prompt: str | None = None
    workedExample: str | None = None
    steps: list[BuildStep] = Field(min_length=1)


class DragArrangeItem(StrictModel):
    id: str
    text: str


class DragArrangeComponent(StrictModel):
    type: Literal["drag_arrange"]
    id: str
    prompt: str
    items: list[DragArrangeItem] = Field(min_length=2)
    hint: str | None = None


class InteractiveWidgetComponent(StrictModel):
    type: Literal["interactive_widget"]
    id: str
    prompt: str | None = None
    required: bool = True
    widget: InteractiveWidgetPayload


class ReflectionSubPrompt(StrictModel):
    id: str
    text: str = Field(validation_alias=AliasChoices("text", "prompt"))
    label: str | None = None
    responseKind: Literal["text", "rating"] = "text"


class ReflectionPromptComponent(StrictModel):
    type: Literal["reflection_prompt"]
    id: str
    prompt: str
    subPrompts: list[ReflectionSubPrompt] = Field(
        min_length=1, validation_alias=AliasChoices("subPrompts", "prompts")
    )
    required: bool = True

    @field_validator("subPrompts", mode="before")
    @classmethod
    def coerce_string_sub_prompts(cls, v: list) -> list:
        coerced: list = []
        for i, item in enumerate(v):
            if isinstance(item, str):
                coerced.append({"id": f"sp-{i + 1}", "text": item})
            else:
                coerced.append(item)
        return coerced


class RubricCriterion(StrictModel):
    id: str
    label: str
    description: str | None = None


class RubricLevel(StrictModel):
    value: int = Field(gt=0)
    label: str
    description: str | None = None


class RubricSelfCheckComponent(StrictModel):
    type: Literal["rubric_self_check"]
    id: str
    prompt: str | None = None
    criteria: list[RubricCriterion] = Field(min_length=1)
    levels: list[RubricLevel] = Field(min_length=2)
    notePrompt: str | None = None


class FileUploadComponent(StrictModel):
    type: Literal["file_upload"]
    id: str
    prompt: str
    accept: list[str] | None = None
    maxFiles: int = Field(default=3, gt=0)
    notePrompt: str | None = None
    required: bool = False


class ImageCaptureComponent(StrictModel):
    type: Literal["image_capture"]
    id: str
    prompt: str
    instructions: str | None = None
    maxImages: int = Field(default=3, gt=0)
    required: bool = False


class AudioCaptureComponent(StrictModel):
    type: Literal["audio_capture"]
    id: str
    prompt: str
    maxDurationSeconds: int | None = Field(default=None, gt=0)
    required: bool = False


class ObservationField(StrictModel):
    id: str
    label: str
    inputKind: Literal["text", "rating", "checkbox"] = "text"


class ObservationRecordComponent(StrictModel):
    type: Literal["observation_record"]
    id: str
    prompt: str
    fields: list[ObservationField] = Field(min_length=1)
    filledBy: Literal["teacher", "parent", "learner"] = "teacher"


class TeacherCheckoffItem(StrictModel):
    id: str
    label: str
    description: str | None = None


class TeacherCheckoffComponent(StrictModel):
    type: Literal["teacher_checkoff"]
    id: str
    prompt: str
    items: list[TeacherCheckoffItem] = Field(min_length=1)
    acknowledgmentLabel: str | None = None
    notePrompt: str | None = None


class CompareAndExplainComponent(StrictModel):
    type: Literal["compare_and_explain"]
    id: str
    prompt: str
    itemA: str = Field(validation_alias=AliasChoices("itemA", "leftLabel"))
    itemB: str = Field(validation_alias=AliasChoices("itemB", "rightLabel"))
    responsePrompt: str | None = None
    required: bool = True


class NextStepChoice(StrictModel):
    id: str
    label: str
    description: str | None = None


class ChooseNextStepComponent(StrictModel):
    type: Literal["choose_next_step"]
    id: str
    prompt: str
    choices: list[NextStepChoice] = Field(min_length=2)


class ConstructionSpaceComponent(StrictModel):
    type: Literal["construction_space"]
    id: str
    prompt: str
    scaffoldText: str | None = None
    hint: str | None = None
    required: bool = True


ActivityComponent = Annotated[
    HeadingComponent
    | ParagraphComponent
    | CalloutComponent
    | ImageComponent
    | DividerComponent
    | ShortAnswerComponent
    | TextResponseComponent
    | RichTextResponseComponent
    | SingleSelectComponent
    | MultiSelectComponent
    | RatingComponent
    | ConfidenceCheckComponent
    | ChecklistComponent
    | OrderedSequenceComponent
    | MatchingPairsComponent
    | CategorizationComponent
    | SortIntoGroupsComponent
    | LabelMapComponent
    | HotspotSelectComponent
    | BuildStepsComponent
    | DragArrangeComponent
    | InteractiveWidgetComponent
    | ReflectionPromptComponent
    | RubricSelfCheckComponent
    | FileUploadComponent
    | ImageCaptureComponent
    | AudioCaptureComponent
    | ObservationRecordComponent
    | TeacherCheckoffComponent
    | CompareAndExplainComponent
    | ChooseNextStepComponent
    | ConstructionSpaceComponent,
    Field(discriminator="type"),
]


def is_interactive_component(component: ActivityComponent) -> bool:
    if component.type in INTERACTIVE_COMPONENT_TYPES:
        return True
    return component.type == "interactive_widget" and widget_accepts_input(component.widget)


class CompletionRules(StrictModel):
    strategy: Literal[
        "all_interactive_components",
        "minimum_components",
        "any_submission",
        "teacher_approval",
    ] = "all_interactive_components"
    minimumComponents: int | None = Field(default=None, gt=0)
    incompleteMessage: str | None = None

    @field_validator("minimumComponents", mode="before")
    @classmethod
    def coerce_zero_to_none(cls, v: int | None) -> int | None:
        if v == 0:
            return None
        return v

    @model_validator(mode="after")
    def validate_minimum_components(self) -> "CompletionRules":
        if self.strategy == "minimum_components" and self.minimumComponents is None:
            raise ValueError("minimumComponents is required when strategy is minimum_components.")
        return self


class EvidenceSchema(StrictModel):
    captureKinds: list[EvidenceKind] = Field(min_length=1)
    requiresReview: bool = False
    autoScorable: bool = False
    reviewerNotes: str | None = None


class ScoringModel(StrictModel):
    mode: ScoringMode
    masteryThreshold: float = Field(default=0.8, ge=0, le=1)
    reviewThreshold: float = Field(default=0.6, ge=0, le=1)
    rubricMasteryLevel: int | None = Field(default=None, gt=0)
    confidenceMasteryLevel: int | None = Field(default=None, ge=1, le=5)
    notes: str | None = None

    @field_validator("rubricMasteryLevel", "confidenceMasteryLevel", mode="before")
    @classmethod
    def coerce_zeroish_optional_levels(cls, value: int | None) -> int | None:
        if value in (0, "0", ""):
            return None
        return value


class AdaptationRules(StrictModel):
    hintStrategy: Literal["on_request", "always", "after_wrong_attempt"] = "on_request"
    allowSkip: bool = False
    allowRetry: bool = False
    maxRetries: int | None = Field(default=None, gt=0)


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


class ActivityMetadata(StrictModel):
    sessionScope: str | None = None
    sessionTitle: str | None = None
    lessonShape: str | None = None
    workflowMode: str | None = None
    subject: str | None = None

    @model_validator(mode="before")
    @classmethod
    def drop_unknown_keys(cls, value):
        if not isinstance(value, dict):
            return value
        allowed = {"sessionScope", "sessionTitle", "lessonShape", "workflowMode", "subject"}
        return {key: item for key, item in value.items() if key in allowed}


class ActivityArtifact(StrictModel):
    schemaVersion: Literal["2"]
    title: str
    purpose: str
    activityKind: ActivityKind
    linkedObjectiveIds: list[str] = Field(default_factory=list)
    linkedSkillTitles: list[str] = Field(default_factory=list)
    estimatedMinutes: int = Field(gt=0)
    interactionMode: InteractionMode
    components: list[ActivityComponent] = Field(min_length=1)
    completionRules: CompletionRules = Field(default_factory=CompletionRules)
    evidenceSchema: EvidenceSchema
    scoringModel: ScoringModel
    adaptationRules: AdaptationRules | None = None
    teacherSupport: TeacherSupport | None = None
    offlineMode: OfflineMode | None = None
    templateHint: ActivityTemplateHint | None = None
    metadata: ActivityMetadata | None = None

    @field_validator("components")
    @classmethod
    def validate_components(cls, value: list[ActivityComponent]) -> list[ActivityComponent]:
        ids = [component.id for component in value]
        if len(ids) != len(set(ids)):
            raise ValueError("Activity artifact component ids must be unique.")
        return value


class RecentLessonOutcome(StrictModel):
    title: str
    status: str
    date: str


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
    feedback_notes: list[str] = Field(default_factory=list)
    recent_lesson_outcomes: list[RecentLessonOutcome] = Field(default_factory=list)
    lesson_draft: StructuredLessonDraft
