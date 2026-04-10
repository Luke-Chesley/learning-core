from __future__ import annotations

import re
from typing import Annotated, Literal

from pydantic import Field, field_validator, model_validator

from learning_core.contracts.base import StrictModel


SurfaceKind = Literal["board_surface", "expression_surface", "graph_surface"]
EngineKind = Literal["chess", "math_symbolic", "graphing"]
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


def _validate_view_only_feedback_semantics(*, mode: str, feedback_mode: FeedbackMode) -> None:
    if mode == "view_only" and feedback_mode != "none":
        raise ValueError("view_only widgets must use feedback.mode='none'.")


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
        _validate_view_only_feedback_semantics(
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
        _validate_view_only_feedback_semantics(
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
        _validate_view_only_feedback_semantics(
            mode=self.interaction.mode,
            feedback_mode=self.feedback.mode,
        )
        return self


InteractiveWidgetPayload = Annotated[
    ChessBoardWidget | MathSymbolicWidget | GraphingWidget,
    Field(discriminator="engineKind"),
]


def widget_accepts_input(widget: InteractiveWidgetPayload) -> bool:
    if widget.engineKind == "chess":
        return widget.interaction.mode == "move_input"
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
