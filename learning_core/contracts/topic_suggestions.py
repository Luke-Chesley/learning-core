from __future__ import annotations

from pydantic import Field, field_validator, model_validator

from learning_core.contracts.base import StrictModel


class TopicSuggestRequest(StrictModel):
    query: str = Field(min_length=2, max_length=120)
    learner: str | None = Field(default=None, max_length=120)
    timeframe: str | None = Field(default=None, max_length=120)
    local_suggestions: list[str] = Field(default_factory=list, max_length=12)
    max_suggestions: int = Field(default=8, ge=1, le=8)

    @field_validator("query", "learner", "timeframe", mode="before")
    @classmethod
    def normalize_text(cls, value):
        if value is None:
            return None
        return " ".join(str(value).split())

    @field_validator("local_suggestions", mode="before")
    @classmethod
    def normalize_local_suggestions(cls, value):
        if not value:
            return []
        return [" ".join(str(item).split()) for item in value if str(item).strip()]


class TopicSuggestion(StrictModel):
    topic: str = Field(min_length=2, max_length=80)

    @field_validator("topic", mode="before")
    @classmethod
    def normalize_topic(cls, value):
        normalized = " ".join(str(value).split()).strip(" .")
        return normalized


class TopicSuggestArtifact(StrictModel):
    suggestions: list[TopicSuggestion] = Field(default_factory=list, max_length=8)

    @field_validator("suggestions", mode="before")
    @classmethod
    def normalize_suggestions(cls, value):
        if not isinstance(value, list):
            return value
        return [
            {"topic": item} if isinstance(item, str) else item
            for item in value
        ]

    @model_validator(mode="after")
    def dedupe_suggestions(self) -> "TopicSuggestArtifact":
        seen: set[str] = set()
        deduped: list[TopicSuggestion] = []
        for suggestion in self.suggestions:
            key = suggestion.topic.casefold()
            if key in seen:
                continue
            seen.add(key)
            deduped.append(suggestion)
        self.suggestions = deduped[:8]
        return self
