from __future__ import annotations

from typing import Literal, TypeAlias
from urllib.parse import urlparse

from pydantic import Field, field_validator, model_validator

from learning_core.contracts.base import StrictModel

LESSON_SHAPE_VALUES = (
    "balanced",
    "direct_instruction",
    "discussion_heavy",
    "project_based",
    "practice_heavy",
    "gentle_short_blocks",
)

LESSON_BLOCK_TYPE_VALUES = (
    "opener",
    "retrieval",
    "warm_up",
    "model",
    "guided_practice",
    "independent_practice",
    "discussion",
    "check_for_understanding",
    "reflection",
    "wrap_up",
    "transition",
    "movement_break",
    "project_work",
    "read_aloud",
    "demonstration",
)

LESSON_VISUAL_AID_ALLOWED_HOSTS = (
    "upload.wikimedia.org",
    "commons.wikimedia.org",
    "wikimedia.org",
    "wikipedia.org",
    "noaa.gov",
    "weather.gov",
    "nasa.gov",
    "images-assets.nasa.gov",
)

LessonShape: TypeAlias = Literal[
    "balanced",
    "direct_instruction",
    "discussion_heavy",
    "project_based",
    "practice_heavy",
    "gentle_short_blocks",
]

LessonBlockType: TypeAlias = Literal[
    "opener",
    "retrieval",
    "warm_up",
    "model",
    "guided_practice",
    "independent_practice",
    "discussion",
    "check_for_understanding",
    "reflection",
    "wrap_up",
    "transition",
    "movement_break",
    "project_work",
    "read_aloud",
    "demonstration",
]

LessonVisualAidKind: TypeAlias = Literal[
    "reference_image",
    "diagram",
    "chart",
    "map",
    "source_image",
]


def validate_lesson_visual_aid_url(value: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("Lesson visual aid URLs must be real http(s) URLs.")

    host = (parsed.hostname or "").lower()
    if not any(host == allowed or host.endswith(f".{allowed}") for allowed in LESSON_VISUAL_AID_ALLOWED_HOSTS):
        raise ValueError("Lesson visual aid URL host is not in the allowlist.")

    return value


class LessonVisualAid(StrictModel):
    id: str
    title: str
    kind: LessonVisualAidKind
    url: str
    alt: str
    caption: str | None = None
    usage_note: str | None = None
    source_name: str | None = None

    @field_validator("url")
    @classmethod
    def validate_url(cls, value: str) -> str:
        return validate_lesson_visual_aid_url(value)


class LessonAdaptation(StrictModel):
    trigger: str
    action: str


class LessonBlock(StrictModel):
    type: LessonBlockType
    title: str
    minutes: int
    purpose: str
    teacher_action: str
    learner_action: str
    check_for: str | None = None
    materials_needed: list[str] = Field(default_factory=list)
    visual_aid_ids: list[str] = Field(default_factory=list)
    optional: bool = False


class StructuredLessonDraft(StrictModel):
    schema_version: Literal["1.0"]
    title: str
    lesson_focus: str
    primary_objectives: list[str] = Field(default_factory=list)
    success_criteria: list[str] = Field(default_factory=list)
    total_minutes: int
    blocks: list[LessonBlock] = Field(default_factory=list)
    visual_aids: list[LessonVisualAid] = Field(default_factory=list)
    materials: list[str] = Field(default_factory=list)
    teacher_notes: list[str] = Field(default_factory=list)
    co_teacher_notes: list[str] = Field(default_factory=list)
    adaptations: list[LessonAdaptation] = Field(default_factory=list)
    assessment_artifact: str | None = None
    lesson_shape: LessonShape | None = None
    prep: list[str] = Field(default_factory=list)
    extension: str | None = None
    follow_through: str | None = None
    accommodations: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_visual_aid_references(self) -> "StructuredLessonDraft":
        visual_aid_ids = {visual_aid.id for visual_aid in self.visual_aids}
        for block in self.blocks:
            for visual_aid_id in block.visual_aid_ids:
                if visual_aid_id not in visual_aid_ids:
                    raise ValueError(f'Unknown visual aid id "{visual_aid_id}".')
        return self
