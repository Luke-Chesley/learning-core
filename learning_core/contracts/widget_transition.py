from __future__ import annotations

import re
from typing import Any, Annotated, Literal

from pydantic import Field, field_validator

from learning_core.contracts.activity import ComponentType
from learning_core.contracts.activity_feedback import ActivityFeedbackArtifact, FeedbackAttemptMetadata
from learning_core.contracts.base import StrictModel
from learning_core.contracts.widgets import EngineKind, InteractiveWidgetPayload, MapCoordinate

_BOARD_SQUARE_PATTERN = re.compile(r"^[a-h][1-8]$")


class ChessMoveInput(StrictModel):
    fromSquare: str | None = None
    toSquare: str | None = None
    promotion: Literal["q", "r", "b", "n"] | None = None
    san: str | None = None
    uci: str | None = None

    @field_validator("fromSquare", "toSquare")
    @classmethod
    def validate_square(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().lower()
        if not _BOARD_SQUARE_PATTERN.fullmatch(normalized):
            raise ValueError("Chess move squares must use algebraic notation like 'e4'.")
        return normalized


class BoardSelectSquareAction(StrictModel):
    type: Literal["select_square"]
    square: str

    @field_validator("square")
    @classmethod
    def validate_square(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not _BOARD_SQUARE_PATTERN.fullmatch(normalized):
            raise ValueError("Squares must use algebraic notation like 'e4'.")
        return normalized


class BoardSubmitMoveAction(StrictModel):
    type: Literal["submit_move"]
    move: ChessMoveInput | str | dict[str, Any]


class BoardResetAction(StrictModel):
    type: Literal["reset"]


class MapSelectFeatureAction(StrictModel):
    type: Literal["select_feature"]
    featureId: str


class MapPlaceMarkerAction(StrictModel):
    type: Literal["place_marker"]
    coordinate: MapCoordinate


class MapSubmitPathAction(StrictModel):
    type: Literal["submit_path"]
    coordinates: list[MapCoordinate] = Field(min_length=2)


class MapSubmitLabelsAction(StrictModel):
    type: Literal["submit_labels"]
    labels: dict[str, str]


class MapToggleLayerAction(StrictModel):
    type: Literal["toggle_layer"]
    layerId: str


class MapSetTimelineYearAction(StrictModel):
    type: Literal["set_timeline_year"]
    year: int


WidgetLearnerAction = Annotated[
    BoardSelectSquareAction
    | BoardSubmitMoveAction
    | BoardResetAction
    | MapSelectFeatureAction
    | MapPlaceMarkerAction
    | MapSubmitPathAction
    | MapSubmitLabelsAction
    | MapToggleLayerAction
    | MapSetTimelineYearAction,
    Field(discriminator="type"),
]


class WidgetTransitionRequest(StrictModel):
    activityId: str | None = None
    componentId: str
    componentType: ComponentType
    widget: InteractiveWidgetPayload
    learnerAction: WidgetLearnerAction
    currentResponse: Any | None = None
    attemptMetadata: FeedbackAttemptMetadata = Field(default_factory=FeedbackAttemptMetadata)


class WidgetTransitionArtifact(StrictModel):
    schemaVersion: Literal["1"]
    componentId: str
    componentType: ComponentType
    widgetEngineKind: EngineKind | None = None
    accepted: bool
    normalizedLearnerAction: Any | None = None
    nextResponse: Any | None = None
    canonicalWidget: InteractiveWidgetPayload
    legalTargets: list[str] = Field(default_factory=list)
    immediateFeedback: ActivityFeedbackArtifact | None = None
    errorMessage: str | None = None
