from __future__ import annotations

import re
from typing import Annotated, Literal

from pydantic import Field, field_validator, model_validator

from learning_core.contracts.base import StrictModel


SurfaceKind = Literal["board_surface", "expression_surface", "graph_surface", "map_surface"]
EngineKind = Literal["chess", "math_symbolic", "graphing", "map_geojson"]
SurfaceRole = Literal["primary", "supporting"]
SubmissionMode = Literal["immediate", "explicit_submit"]
SelectionMode = Literal["click_click", "drag_drop", "either"]
FeedbackMode = Literal["none", "immediate", "explicit_submit"]
FeedbackDisplayMode = Literal["inline", "banner"]
ResetPolicy = Literal["not_allowed", "reset_to_initial"]
AttemptPolicy = Literal["single_attempt", "allow_retry"]

_BOARD_SQUARE_PATTERN = re.compile(r"^[a-h][1-8]$")


def _normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _validate_reset_semantics(*, allow_reset: bool, reset_policy: ResetPolicy, attempt_policy: AttemptPolicy) -> bool:
    if allow_reset and reset_policy == "not_allowed":
        raise ValueError("allowReset cannot be true when resetPolicy is 'not_allowed'.")
    if not allow_reset and reset_policy != "not_allowed":
        raise ValueError("resetPolicy must be 'not_allowed' when allowReset is false.")
    if attempt_policy == "single_attempt" and allow_reset:
        raise ValueError("single_attempt widgets cannot allow reset.")
    return allow_reset


def _validate_feedback_semantics(*, submission_mode: SubmissionMode, feedback_mode: FeedbackMode) -> None:
    if feedback_mode == "explicit_submit" and submission_mode != "explicit_submit":
        raise ValueError("feedback.mode='explicit_submit' requires interaction.submissionMode='explicit_submit'.")


def _coerce_view_only_feedback(*, mode: str, feedback_mode: FeedbackMode) -> FeedbackMode:
    if mode == "view_only" and feedback_mode != "none":
        return "none"
    return feedback_mode


_BOARD_INTERACTION_MODE_ALIASES: dict[str, str] = {
    "inspect": "view_only",
    "observe": "view_only",
    "readonly": "view_only",
    "read_only": "view_only",
}

_EXPRESSION_INTERACTION_MODE_ALIASES: dict[str, str] = {
    "inspect": "view_only",
    "observe": "view_only",
    "readonly": "view_only",
    "read_only": "view_only",
}

_GRAPH_INTERACTION_MODE_ALIASES: dict[str, str] = {
    "inspect": "view_only",
    "observe": "view_only",
    "readonly": "view_only",
    "read_only": "view_only",
}

_MAP_INTERACTION_MODE_ALIASES: dict[str, str] = {
    "inspect": "view_only",
    "observe": "view_only",
    "readonly": "view_only",
    "read_only": "view_only",
    "explore": "guided_explore",
}


class BoardArrow(StrictModel):
    fromSquare: str
    toSquare: str
    color: Literal["green", "blue", "yellow", "red"] = "green"

    @field_validator("fromSquare", "toSquare")
    @classmethod
    def validate_square(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not _BOARD_SQUARE_PATTERN.fullmatch(normalized):
            raise ValueError("Board squares must use algebraic notation like 'e4'.")
        return normalized


class BoardSurfaceConfig(StrictModel):
    orientation: Literal["white", "black"] = "white"


class BoardSurfaceDisplay(StrictModel):
    showSideToMove: bool = True
    showCoordinates: bool = True
    showMoveHint: bool = True
    boardRole: SurfaceRole = "primary"


class BoardSurfaceState(StrictModel):
    fen: str
    initialFen: str | None = None

    @field_validator("fen", "initialFen")
    @classmethod
    def validate_fen(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("state.fen is required.")
        return normalized

    @model_validator(mode="after")
    def populate_initial_fen(self) -> "BoardSurfaceState":
        if self.initialFen is None:
            self.initialFen = self.fen
        return self


class BoardSurfaceInteraction(StrictModel):
    mode: Literal["view_only", "move_input"] = "view_only"
    submissionMode: SubmissionMode = "immediate"
    selectionMode: SelectionMode = "either"
    showLegalTargets: bool = True
    allowReset: bool = True
    resetPolicy: ResetPolicy = "reset_to_initial"
    attemptPolicy: AttemptPolicy = "allow_retry"

    @field_validator("mode", mode="before")
    @classmethod
    def normalize_mode_alias(cls, value: str) -> str:
        if isinstance(value, str):
            return _BOARD_INTERACTION_MODE_ALIASES.get(value.strip().lower(), value)
        return value

    @model_validator(mode="after")
    def validate_reset_policy(self) -> "BoardSurfaceInteraction":
        self.allowReset = _validate_reset_semantics(
            allow_reset=self.allowReset,
            reset_policy=self.resetPolicy,
            attempt_policy=self.attemptPolicy,
        )
        return self


class BoardSurfaceFeedback(StrictModel):
    mode: FeedbackMode = "immediate"
    displayMode: FeedbackDisplayMode = "inline"


class ChessEvaluationConfig(StrictModel):
    expectedMoves: list[str] = Field(default_factory=list)


class BoardSurfaceAnnotations(StrictModel):
    highlightSquares: list[str] = Field(default_factory=list)
    arrows: list[BoardArrow] = Field(default_factory=list)

    @field_validator("highlightSquares")
    @classmethod
    def validate_highlight_squares(cls, values: list[str]) -> list[str]:
        normalized_values: list[str] = []
        for value in values:
            normalized = value.strip().lower()
            if not _BOARD_SQUARE_PATTERN.fullmatch(normalized):
                raise ValueError("highlightSquares must use algebraic notation like 'e4'.")
            normalized_values.append(normalized)
        return normalized_values


class ChessBoardWidget(StrictModel):
    surfaceKind: Literal["board_surface"]
    engineKind: Literal["chess"]
    version: Literal["1"] = "1"
    instructionText: str | None = None
    caption: str | None = None
    surface: BoardSurfaceConfig = Field(default_factory=BoardSurfaceConfig)
    display: BoardSurfaceDisplay = Field(default_factory=BoardSurfaceDisplay)
    state: BoardSurfaceState
    interaction: BoardSurfaceInteraction = Field(default_factory=BoardSurfaceInteraction)
    feedback: BoardSurfaceFeedback = Field(default_factory=BoardSurfaceFeedback)
    evaluation: ChessEvaluationConfig = Field(default_factory=ChessEvaluationConfig)
    annotations: BoardSurfaceAnnotations = Field(default_factory=BoardSurfaceAnnotations)

    _normalize_instruction_text = field_validator("instructionText", mode="before")(_normalize_optional_text)
    _normalize_caption = field_validator("caption", mode="before")(_normalize_optional_text)

    @model_validator(mode="after")
    def validate_runtime_semantics(self) -> "ChessBoardWidget":
        _validate_feedback_semantics(
            submission_mode=self.interaction.submissionMode,
            feedback_mode=self.feedback.mode,
        )
        self.feedback.mode = _coerce_view_only_feedback(
            mode=self.interaction.mode,
            feedback_mode=self.feedback.mode,
        )
        return self


class ExpressionSurfaceConfig(StrictModel):
    placeholder: str | None = None
    mathKeyboard: bool = False


class ExpressionSurfaceDisplay(StrictModel):
    surfaceRole: SurfaceRole = "primary"
    showPromptLatex: bool = True


class ExpressionSurfaceState(StrictModel):
    promptLatex: str | None = None
    initialValue: str | None = None


class ExpressionSurfaceInteraction(StrictModel):
    mode: Literal["view_only", "expression_entry", "equation_entry", "step_entry"] = "expression_entry"
    submissionMode: SubmissionMode = "explicit_submit"
    allowReset: bool = True
    resetPolicy: ResetPolicy = "reset_to_initial"
    attemptPolicy: AttemptPolicy = "allow_retry"

    @field_validator("mode", mode="before")
    @classmethod
    def normalize_mode_alias(cls, value: str) -> str:
        if isinstance(value, str):
            return _EXPRESSION_INTERACTION_MODE_ALIASES.get(value.strip().lower(), value)
        return value

    @model_validator(mode="after")
    def validate_reset_policy(self) -> "ExpressionSurfaceInteraction":
        self.allowReset = _validate_reset_semantics(
            allow_reset=self.allowReset,
            reset_policy=self.resetPolicy,
            attempt_policy=self.attemptPolicy,
        )
        return self


class ExpressionSurfaceFeedback(StrictModel):
    mode: FeedbackMode = "explicit_submit"
    displayMode: FeedbackDisplayMode = "inline"


class MathSymbolicEvaluationConfig(StrictModel):
    expectedExpression: str | None = None
    equivalenceMode: Literal["exact", "simplified", "equivalent"] = "equivalent"


class ExpressionSurfaceAnnotations(StrictModel):
    helperText: str | None = None


class MathSymbolicWidget(StrictModel):
    surfaceKind: Literal["expression_surface"]
    engineKind: Literal["math_symbolic"]
    version: Literal["1"] = "1"
    instructionText: str | None = None
    caption: str | None = None
    surface: ExpressionSurfaceConfig = Field(default_factory=ExpressionSurfaceConfig)
    display: ExpressionSurfaceDisplay = Field(default_factory=ExpressionSurfaceDisplay)
    state: ExpressionSurfaceState = Field(default_factory=ExpressionSurfaceState)
    interaction: ExpressionSurfaceInteraction = Field(default_factory=ExpressionSurfaceInteraction)
    feedback: ExpressionSurfaceFeedback = Field(default_factory=ExpressionSurfaceFeedback)
    evaluation: MathSymbolicEvaluationConfig = Field(default_factory=MathSymbolicEvaluationConfig)
    annotations: ExpressionSurfaceAnnotations = Field(default_factory=ExpressionSurfaceAnnotations)

    _normalize_instruction_text = field_validator("instructionText", mode="before")(_normalize_optional_text)
    _normalize_caption = field_validator("caption", mode="before")(_normalize_optional_text)

    @model_validator(mode="after")
    def validate_runtime_semantics(self) -> "MathSymbolicWidget":
        _validate_feedback_semantics(
            submission_mode=self.interaction.submissionMode,
            feedback_mode=self.feedback.mode,
        )
        self.feedback.mode = _coerce_view_only_feedback(
            mode=self.interaction.mode,
            feedback_mode=self.feedback.mode,
        )
        return self


class GraphSurfaceConfig(StrictModel):
    xLabel: str | None = None
    yLabel: str | None = None
    grid: bool = True


class GraphSurfaceDisplay(StrictModel):
    surfaceRole: SurfaceRole = "primary"
    showAxisLabels: bool = True


class GraphSurfaceState(StrictModel):
    prompt: str | None = None
    initialExpression: str | None = None


class GraphSurfaceInteraction(StrictModel):
    mode: Literal["view_only", "plot_point", "plot_curve", "analyze_graph"] = "plot_point"
    submissionMode: SubmissionMode = "explicit_submit"
    allowReset: bool = True
    resetPolicy: ResetPolicy = "reset_to_initial"
    attemptPolicy: AttemptPolicy = "allow_retry"

    @field_validator("mode", mode="before")
    @classmethod
    def normalize_mode_alias(cls, value: str) -> str:
        if isinstance(value, str):
            return _GRAPH_INTERACTION_MODE_ALIASES.get(value.strip().lower(), value)
        return value

    @model_validator(mode="after")
    def validate_reset_policy(self) -> "GraphSurfaceInteraction":
        self.allowReset = _validate_reset_semantics(
            allow_reset=self.allowReset,
            reset_policy=self.resetPolicy,
            attempt_policy=self.attemptPolicy,
        )
        return self


class GraphSurfaceFeedback(StrictModel):
    mode: FeedbackMode = "explicit_submit"
    displayMode: FeedbackDisplayMode = "inline"


class GraphingEvaluationConfig(StrictModel):
    expectedGraphDescription: str | None = None


class GraphSurfaceAnnotations(StrictModel):
    overlayText: str | None = None


class GraphingWidget(StrictModel):
    surfaceKind: Literal["graph_surface"]
    engineKind: Literal["graphing"]
    version: Literal["1"] = "1"
    instructionText: str | None = None
    caption: str | None = None
    surface: GraphSurfaceConfig = Field(default_factory=GraphSurfaceConfig)
    display: GraphSurfaceDisplay = Field(default_factory=GraphSurfaceDisplay)
    state: GraphSurfaceState = Field(default_factory=GraphSurfaceState)
    interaction: GraphSurfaceInteraction = Field(default_factory=GraphSurfaceInteraction)
    feedback: GraphSurfaceFeedback = Field(default_factory=GraphSurfaceFeedback)
    evaluation: GraphingEvaluationConfig = Field(default_factory=GraphingEvaluationConfig)
    annotations: GraphSurfaceAnnotations = Field(default_factory=GraphSurfaceAnnotations)

    _normalize_instruction_text = field_validator("instructionText", mode="before")(_normalize_optional_text)
    _normalize_caption = field_validator("caption", mode="before")(_normalize_optional_text)

    @model_validator(mode="after")
    def validate_runtime_semantics(self) -> "GraphingWidget":
        _validate_feedback_semantics(
            submission_mode=self.interaction.submissionMode,
            feedback_mode=self.feedback.mode,
        )
        self.feedback.mode = _coerce_view_only_feedback(
            mode=self.interaction.mode,
            feedback_mode=self.feedback.mode,
        )
        return self


class MapCoordinate(StrictModel):
    lon: float = Field(ge=-180, le=180)
    lat: float = Field(ge=-90, le=90)


class MapBounds(StrictModel):
    west: float = Field(ge=-180, le=180)
    south: float = Field(ge=-90, le=90)
    east: float = Field(ge=-180, le=180)
    north: float = Field(ge=-90, le=90)

    @model_validator(mode="after")
    def validate_bounds(self) -> "MapBounds":
        if self.west >= self.east:
            raise ValueError("Map bounds must satisfy west < east.")
        if self.south >= self.north:
            raise ValueError("Map bounds must satisfy south < north.")
        return self


class MapSurfaceConfig(StrictModel):
    projection: Literal["web_mercator", "equal_earth", "equirectangular", "albers_usa"] = "equal_earth"
    basemapStyle: Literal["none", "light", "terrain", "satellite"] = "none"
    center: MapCoordinate = Field(default_factory=lambda: MapCoordinate(lon=0.0, lat=20.0))
    zoom: float = Field(default=2.0, ge=0.5, le=18.0)
    bounds: MapBounds | None = None


class MapSurfaceDisplay(StrictModel):
    surfaceRole: SurfaceRole = "primary"
    showLegend: bool = True
    showLabels: bool = True
    showInstructionsPanel: bool = True
    allowLayerToggle: bool = True


class MapLayerConfig(StrictModel):
    id: str
    sourceId: str
    featureIds: list[str] = Field(default_factory=list)
    labelField: str | None = None
    visible: bool = True
    stylePreset: Literal["political", "physical", "historical", "climate", "route", "custom"] = "political"


class MapSurfaceState(StrictModel):
    sourceId: str
    activeLayerIds: list[str] = Field(default_factory=list)
    selectedFeatureIds: list[str] = Field(default_factory=list)
    markerCoordinate: MapCoordinate | None = None
    drawnPath: list[MapCoordinate] = Field(default_factory=list)
    labelAssignments: dict[str, str] = Field(default_factory=dict)
    timelineYear: int | None = None


class MapSurfaceInteraction(StrictModel):
    mode: Literal[
        "view_only",
        "guided_explore",
        "select_region",
        "multi_select_regions",
        "place_marker",
        "trace_path",
        "label_regions",
        "compare_layers",
        "timeline_scrub",
    ] = "guided_explore"
    submissionMode: SubmissionMode = "explicit_submit"
    allowReset: bool = True
    resetPolicy: ResetPolicy = "reset_to_initial"
    attemptPolicy: AttemptPolicy = "allow_retry"
    selectionBehavior: Literal["single", "multiple"] = "single"

    @field_validator("mode", mode="before")
    @classmethod
    def normalize_mode_alias(cls, value: str) -> str:
        if isinstance(value, str):
            return _MAP_INTERACTION_MODE_ALIASES.get(value.strip().lower(), value)
        return value

    @model_validator(mode="after")
    def validate_reset_policy(self) -> "MapSurfaceInteraction":
        self.allowReset = _validate_reset_semantics(
            allow_reset=self.allowReset,
            reset_policy=self.resetPolicy,
            attempt_policy=self.attemptPolicy,
        )
        if self.mode in {"view_only", "guided_explore", "compare_layers", "timeline_scrub"} and self.submissionMode == "explicit_submit":
            self.submissionMode = "immediate"
        if self.mode == "select_region":
            self.selectionBehavior = "single"
        if self.mode == "multi_select_regions":
            self.selectionBehavior = "multiple"
        return self


class MapSurfaceFeedback(StrictModel):
    mode: FeedbackMode = "explicit_submit"
    displayMode: FeedbackDisplayMode = "inline"


class MapMarkerTarget(StrictModel):
    coordinate: MapCoordinate
    toleranceKm: float = Field(default=50.0, gt=0)


class MapPathTarget(StrictModel):
    coordinates: list[MapCoordinate] = Field(min_length=2)
    toleranceKm: float = Field(default=100.0, gt=0)


class MapLabelTarget(StrictModel):
    featureId: str
    correctLabel: str


class MapGeoJsonEvaluationConfig(StrictModel):
    acceptedFeatureIds: list[str] = Field(default_factory=list)
    featureSelectionMode: Literal["exact", "superset_ok"] = "exact"
    requiredCount: int | None = Field(default=None, ge=1)
    markerTarget: MapMarkerTarget | None = None
    expectedPath: MapPathTarget | None = None
    labelTargets: list[MapLabelTarget] = Field(default_factory=list)
    minimumCoverage: float = Field(default=1.0, ge=0, le=1)


class MapCallout(StrictModel):
    id: str
    text: str
    coordinate: MapCoordinate | None = None
    featureId: str | None = None


class MapSurfaceAnnotations(StrictModel):
    legendTitle: str | None = None
    guidedPrompts: list[str] = Field(default_factory=list)
    callouts: list[MapCallout] = Field(default_factory=list)
    teacherNotes: str | None = None

    @field_validator("callouts", mode="before")
    @classmethod
    def normalize_callouts(cls, value):
        if value is None:
            return []
        if not isinstance(value, list):
            return value
        normalized: list[object] = []
        for index, item in enumerate(value, start=1):
            if isinstance(item, str):
                normalized.append({"id": f"callout-{index}", "text": item})
                continue
            if isinstance(item, dict) and "id" not in item and isinstance(item.get("text"), str):
                normalized.append({"id": f"callout-{index}", **item})
                continue
            normalized.append(item)
        return normalized


class MapGeoJsonWidget(StrictModel):
    surfaceKind: Literal["map_surface"]
    engineKind: Literal["map_geojson"]
    version: Literal["1"] = "1"
    instructionText: str | None = None
    caption: str | None = None
    surface: MapSurfaceConfig = Field(default_factory=MapSurfaceConfig)
    display: MapSurfaceDisplay = Field(default_factory=MapSurfaceDisplay)
    state: MapSurfaceState
    interaction: MapSurfaceInteraction = Field(default_factory=MapSurfaceInteraction)
    feedback: MapSurfaceFeedback = Field(default_factory=MapSurfaceFeedback)
    layers: list[MapLayerConfig] = Field(default_factory=list, min_length=1)
    evaluation: MapGeoJsonEvaluationConfig = Field(default_factory=MapGeoJsonEvaluationConfig)
    annotations: MapSurfaceAnnotations = Field(default_factory=MapSurfaceAnnotations)

    _normalize_instruction_text = field_validator("instructionText", mode="before")(_normalize_optional_text)
    _normalize_caption = field_validator("caption", mode="before")(_normalize_optional_text)

    @model_validator(mode="after")
    def validate_runtime_semantics(self) -> "MapGeoJsonWidget":
        _validate_feedback_semantics(
            submission_mode=self.interaction.submissionMode,
            feedback_mode=self.feedback.mode,
        )
        self.feedback.mode = _coerce_view_only_feedback(
            mode=self.interaction.mode,
            feedback_mode=self.feedback.mode,
        )
        if self.interaction.mode in {"guided_explore", "compare_layers", "timeline_scrub"}:
            self.feedback.mode = "none"
        if self.interaction.mode == "select_region" and self.interaction.selectionBehavior != "single":
            raise ValueError("select_region widgets must use selectionBehavior='single'.")
        if self.interaction.mode == "multi_select_regions" and self.interaction.selectionBehavior != "multiple":
            raise ValueError("multi_select_regions widgets must use selectionBehavior='multiple'.")
        if self.interaction.mode in {"select_region", "multi_select_regions"} and not self.evaluation.acceptedFeatureIds:
            raise ValueError("Region-selection map widgets require evaluation.acceptedFeatureIds.")
        if self.interaction.mode == "place_marker" and self.evaluation.markerTarget is None:
            raise ValueError("place_marker map widgets require evaluation.markerTarget.")
        if self.interaction.mode == "trace_path" and self.evaluation.expectedPath is None:
            raise ValueError("trace_path map widgets require evaluation.expectedPath.")
        if self.interaction.mode == "label_regions" and not self.evaluation.labelTargets:
            raise ValueError("label_regions map widgets require evaluation.labelTargets.")
        if self.interaction.mode == "compare_layers" and len(self.layers) < 2:
            raise ValueError("compare_layers map widgets require at least two layers.")
        return self


InteractiveWidgetPayload = Annotated[
    ChessBoardWidget | MathSymbolicWidget | GraphingWidget | MapGeoJsonWidget,
    Field(discriminator="engineKind"),
]


def widget_accepts_input(widget: InteractiveWidgetPayload) -> bool:
    if widget.engineKind == "chess":
        return widget.interaction.mode == "move_input"
    if widget.engineKind == "map_geojson":
        return widget.interaction.mode in {
            "select_region",
            "multi_select_regions",
            "place_marker",
            "trace_path",
            "label_regions",
        }
    return widget.interaction.mode != "view_only"


def widget_surface_role(widget: InteractiveWidgetPayload) -> SurfaceRole:
    if widget.engineKind == "chess":
        return widget.display.boardRole
    return widget.display.surfaceRole


def widget_allows_reset(widget: InteractiveWidgetPayload) -> bool:
    return getattr(widget.interaction, "allowReset", False) and widget.interaction.resetPolicy != "not_allowed"


def widget_instruction_text(widget: InteractiveWidgetPayload) -> str | None:
    return getattr(widget, "instructionText", None)


def widget_caption(widget: InteractiveWidgetPayload) -> str | None:
    return getattr(widget, "caption", None)
