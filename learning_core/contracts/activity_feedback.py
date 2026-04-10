from __future__ import annotations

from typing import Any, Literal

from pydantic import Field

from learning_core.contracts.activity import ActivityArtifact, ComponentType
from learning_core.contracts.base import StrictModel
from learning_core.contracts.widgets import EngineKind, InteractiveWidgetPayload


ActivityFeedbackStatus = Literal["correct", "incorrect", "partial", "needs_review"]


class FeedbackAttemptMetadata(StrictModel):
    attemptId: str | None = None
    attemptNumber: int | None = Field(default=None, ge=1)
    retryCount: int | None = Field(default=None, ge=0)
    source: Literal["component_action", "autosave", "submit"] | None = None
    timeSpentMs: int | None = Field(default=None, ge=0)


class FeedbackScoring(StrictModel):
    score: float | None = Field(default=None, ge=0, le=1)
    matchedTargets: int | None = Field(default=None, ge=0)
    totalTargets: int | None = Field(default=None, ge=0)
    rubricNotes: str | None = None


class ActivityFeedbackArtifact(StrictModel):
    schemaVersion: Literal["1"]
    componentId: str
    componentType: ComponentType
    widgetEngineKind: EngineKind | None = None
    status: ActivityFeedbackStatus
    feedbackMessage: str
    hint: str | None = None
    nextStep: str | None = None
    confidence: float = Field(ge=0, le=1)
    allowRetry: bool = True
    evaluationMethod: Literal["deterministic", "llm"]
    scoring: FeedbackScoring | None = None


class ActivityFeedbackRequest(StrictModel):
    activityId: str | None = None
    activitySpec: ActivityArtifact | None = None
    componentId: str
    componentType: ComponentType
    widget: InteractiveWidgetPayload | None = None
    learnerResponse: Any
    expectedAnswer: Any | None = None
    attemptMetadata: FeedbackAttemptMetadata = Field(default_factory=FeedbackAttemptMetadata)
