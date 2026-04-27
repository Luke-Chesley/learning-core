from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import Field, field_validator, model_validator

from learning_core.contracts.base import StrictModel


GuidanceMode = Literal["preteach", "lesson_review", "misconception_repair"]

_BANNED_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b(compliance|legally compliant|guarantee[sd]?)\b", re.IGNORECASE),
    re.compile(r"\b(accredit(?:ed|ation)|school[- ]approved|state[- ]approved)\b", re.IGNORECASE),
    re.compile(r"\b(public school|private school|charter school|school district)\b", re.IGNORECASE),
    re.compile(r"\bAI (?:teacher|tutor|instructor)\b", re.IGNORECASE),
    re.compile(r"\bdiagnos(?:e|is|tic)\b", re.IGNORECASE),
    re.compile(r"\b(state law|legal requirement|required by law)\b", re.IGNORECASE),
)


def _normalize_text(value: Any) -> Any:
    if value is None:
        return None
    return " ".join(str(value).split())


def _validate_safe_text(value: str | None, *, max_words: int = 60) -> str | None:
    if value is None:
        return None
    normalized = _normalize_text(value)
    if not normalized:
        raise ValueError("Text cannot be blank.")
    if len(normalized.split()) > max_words:
        raise ValueError(f"Text must stay short and scannable ({max_words} words or fewer).")
    for pattern in _BANNED_PATTERNS:
        if pattern.search(normalized):
            raise ValueError("Teaching guide text cannot include legal guarantees, accreditation claims, school claims, AI-teacher claims, diagnosis language, or unsupported state-law certainty.")
    return normalized


class VocabularyItem(StrictModel):
    term: str = Field(min_length=1, max_length=80)
    parent_friendly_definition: str = Field(min_length=1, max_length=240)
    use_in_sentence: str | None = Field(default=None, max_length=180)

    @field_validator("term", "parent_friendly_definition", "use_in_sentence", mode="before")
    @classmethod
    def normalize_text_fields(cls, value):
        return _validate_safe_text(value, max_words=35)


class ParentBrief(StrictModel):
    summary: str = Field(min_length=1, max_length=360)
    why_it_matters: str | None = Field(default=None, max_length=240)
    time_needed_minutes: int | None = Field(default=None, ge=1, le=60)
    materials: list[str] = Field(default_factory=list, max_length=8)

    @field_validator("summary", "why_it_matters", mode="before")
    @classmethod
    def normalize_text_fields(cls, value):
        return _validate_safe_text(value, max_words=60)

    @field_validator("materials", mode="before")
    @classmethod
    def normalize_materials(cls, value):
        if not value:
            return []
        return [_validate_safe_text(item, max_words=8) for item in value if str(item).strip()]


class TeachItPlan(StrictModel):
    setup: str = Field(min_length=1, max_length=300)
    steps: list[str] = Field(min_length=2, max_length=6)
    vocabulary: list[VocabularyItem] = Field(default_factory=list, max_length=8)
    worked_example: str | None = Field(default=None, max_length=300)

    @field_validator("setup", "worked_example", mode="before")
    @classmethod
    def normalize_text_fields(cls, value):
        return _validate_safe_text(value, max_words=55)

    @field_validator("steps", mode="before")
    @classmethod
    def normalize_steps(cls, value):
        if not isinstance(value, list):
            return value
        return [_validate_safe_text(item, max_words=35) for item in value if str(item).strip()]


class GuidedQuestion(StrictModel):
    question: str = Field(min_length=1, max_length=220)
    listen_for: str = Field(min_length=1, max_length=220)
    follow_up: str | None = Field(default=None, max_length=220)

    @field_validator("question", "listen_for", "follow_up", mode="before")
    @classmethod
    def normalize_text_fields(cls, value):
        return _validate_safe_text(value, max_words=35)


class MisconceptionRepair(StrictModel):
    misconception: str = Field(min_length=1, max_length=240)
    why_it_happens: str | None = Field(default=None, max_length=220)
    repair_move: str = Field(min_length=1, max_length=260)
    easier_examples: list[str] = Field(min_length=3, max_length=3)

    @field_validator("misconception", "why_it_happens", "repair_move", mode="before")
    @classmethod
    def normalize_text_fields(cls, value):
        return _validate_safe_text(value, max_words=45)

    @field_validator("easier_examples", mode="before")
    @classmethod
    def normalize_examples(cls, value):
        if not isinstance(value, list):
            return value
        return [_validate_safe_text(item, max_words=18) for item in value if str(item).strip()]


class PracticePlan(StrictModel):
    quick_warmup: str | None = Field(default=None, max_length=220)
    parent_moves: list[str] = Field(min_length=1, max_length=5)
    independent_try: str | None = Field(default=None, max_length=220)

    @field_validator("quick_warmup", "independent_try", mode="before")
    @classmethod
    def normalize_text_fields(cls, value):
        return _validate_safe_text(value, max_words=35)

    @field_validator("parent_moves", mode="before")
    @classmethod
    def normalize_moves(cls, value):
        if not isinstance(value, list):
            return value
        return [_validate_safe_text(item, max_words=35) for item in value if str(item).strip()]


class CheckUnderstandingPlan(StrictModel):
    prompts: list[str] = Field(min_length=1, max_length=4)
    evidence_of_understanding: list[str] = Field(min_length=1, max_length=4)
    if_stuck: str | None = Field(default=None, max_length=220)
    if_ready: str | None = Field(default=None, max_length=220)

    @field_validator("prompts", "evidence_of_understanding", mode="before")
    @classmethod
    def normalize_lists(cls, value):
        if not isinstance(value, list):
            return value
        return [_validate_safe_text(item, max_words=28) for item in value if str(item).strip()]

    @field_validator("if_stuck", "if_ready", mode="before")
    @classmethod
    def normalize_text_fields(cls, value):
        return _validate_safe_text(value, max_words=35)


class AdaptationMove(StrictModel):
    signal: str = Field(min_length=1, max_length=200)
    move: str = Field(min_length=1, max_length=220)

    @field_validator("signal", "move", mode="before")
    @classmethod
    def normalize_text_fields(cls, value):
        return _validate_safe_text(value, max_words=30)


class RecordkeepingSuggestion(StrictModel):
    note: str = Field(min_length=1, max_length=220)
    evidence_to_save: str | None = Field(default=None, max_length=180)

    @field_validator("note", "evidence_to_save", mode="before")
    @classmethod
    def normalize_text_fields(cls, value):
        return _validate_safe_text(value, max_words=35)


class TeachingGuideGenerationRequest(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    lesson: dict[str, Any] | None = None
    existing_session_artifact: dict[str, Any] | None = None
    source_context: dict[str, Any] | None = None
    route_items: list[dict[str, Any]] = Field(default_factory=list)
    learner_context: dict[str, Any] | None = None
    teacher_context: dict[str, Any] | None = None
    activity_summary: dict[str, Any] | None = None
    state_reporting_context: dict[str, Any] | None = None
    guidance_mode: GuidanceMode = "preteach"

    @field_validator("schema_version", mode="before")
    @classmethod
    def normalize_schema_version(cls, value):
        if value in (1, 1.0):
            return "1.0"
        return str(value)

    @model_validator(mode="after")
    def validate_lesson_basis(self) -> "TeachingGuideGenerationRequest":
        if not self.lesson and not self.existing_session_artifact:
            raise ValueError("teaching_guide_generate requires lesson or existing_session_artifact.")
        return self


class TeachingGuideArtifact(StrictModel):
    title: str = Field(min_length=1, max_length=140)
    audience: Literal["parent"]
    guidance_mode: GuidanceMode
    lesson_focus: str = Field(min_length=1, max_length=260)
    parent_brief: ParentBrief
    teach_it: TeachItPlan
    guided_questions: list[GuidedQuestion] = Field(default_factory=list, max_length=6)
    common_misconceptions: list[MisconceptionRepair] = Field(default_factory=list, max_length=4)
    practice_plan: PracticePlan
    check_understanding: CheckUnderstandingPlan
    adaptation_moves: list[AdaptationMove] = Field(default_factory=list, max_length=5)
    recordkeeping: list[RecordkeepingSuggestion] = Field(default_factory=list, max_length=4)
    outsource_flags: list[str] = Field(default_factory=list, max_length=6)
    adult_review_required: bool = False

    @field_validator("title", "lesson_focus", mode="before")
    @classmethod
    def normalize_text_fields(cls, value):
        return _validate_safe_text(value, max_words=35)

    @field_validator("outsource_flags", mode="before")
    @classmethod
    def normalize_flags(cls, value):
        if not value:
            return []
        return [_validate_safe_text(item, max_words=8) for item in value if str(item).strip()]

    @model_validator(mode="after")
    def validate_teaching_guide(self) -> "TeachingGuideArtifact":
        thin_or_review = self.adult_review_required or any(
            flag.casefold() in {"thin_source", "missing_context", "needs_adult_review"}
            for flag in self.outsource_flags
        )
        if self.guidance_mode == "preteach" and len(self.guided_questions) < 2 and not thin_or_review:
            raise ValueError("preteach teaching guides require at least two guided_questions unless adult review is required or the source is thin.")
        if not self.common_misconceptions and not thin_or_review:
            raise ValueError("teaching guides require at least one common_misconception when source context is sufficient.")
        return self
