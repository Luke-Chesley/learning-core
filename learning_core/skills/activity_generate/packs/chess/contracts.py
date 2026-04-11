from __future__ import annotations

from typing import Any, Literal

from pydantic import Field

from learning_core.contracts.base import StrictModel


ChessTaskKind = Literal["escape_check", "best_move", "identify_threat"]
ChessConceptTarget = Literal["move", "block", "capture", "none"]
ChessRoleInActivity = Literal["model", "guided_practice", "check_for_understanding", "recap"]
ChessAcceptanceMode = Literal["engine_derived_escape_set", "single_move", "analysis_only"]


class ChessExamplePlanSlot(StrictModel):
    slotId: str
    taskKind: ChessTaskKind
    conceptTarget: ChessConceptTarget
    roleInActivity: ChessRoleInActivity
    difficulty: str | None = None
    requiresExplanation: bool = False
    acceptanceMode: ChessAcceptanceMode = "engine_derived_escape_set"


class ChessExamplePlan(StrictModel):
    lessonFamily: str = "escape_check_responses"
    allowAdditionalBoardExamples: bool = False
    exampleSlots: list[ChessExamplePlanSlot] = Field(min_length=1)


class ChessValidatedExample(StrictModel):
    slotId: str
    componentId: str
    taskKind: ChessTaskKind
    conceptTarget: ChessConceptTarget
    roleInActivity: ChessRoleInActivity
    acceptanceMode: ChessAcceptanceMode
    difficulty: str | None = None
    requiresExplanation: bool = False
    fen: str
    sideToMove: Literal["white", "black"]
    isCheck: bool
    normalizedAcceptedMoves: list[str]
    acceptedMoveDetails: list[dict[str, Any]]
    engineNotes: list[str] = Field(default_factory=list)
    widgetConfig: dict[str, Any]


class ChessValidatedExampleSet(StrictModel):
    lessonFamily: str = "escape_check_responses"
    allowAdditionalBoardExamples: bool = False
    plan: ChessExamplePlan
    validatedExamples: list[ChessValidatedExample] = Field(min_length=1)


class ChessAcceptedMove(StrictModel):
    uci: str
    san: str
    fromSquare: str
    toSquare: str
    moveCategory: ChessConceptTarget


class ChessComponentTemplate(StrictModel):
    componentId: str
    slotId: str
    roleInActivity: ChessRoleInActivity
    taskKind: ChessTaskKind
    conceptTarget: ChessConceptTarget
    promptHint: str
    widget: dict


class ChessBuiltExample(StrictModel):
    slotId: str
    componentId: str
    taskKind: ChessTaskKind
    conceptTarget: ChessConceptTarget
    roleInActivity: ChessRoleInActivity
    acceptanceMode: ChessAcceptanceMode
    difficulty: str | None = None
    requiresExplanation: bool = False
    fen: str
    sideToMove: Literal["white", "black"]
    isCheck: bool
    acceptedMoves: list[ChessAcceptedMove] = Field(min_length=1)
    engineSummary: str
    widget: dict


class ChessBuiltExampleSet(StrictModel):
    lessonFamily: str = "escape_check"
    examples: list[ChessBuiltExample] = Field(min_length=1)


class ChessValidationReport(StrictModel):
    valid: bool
    hardErrors: list[str] = Field(default_factory=list)
    softWarnings: list[str] = Field(default_factory=list)
    matchedSlots: list[str] = Field(default_factory=list)
    missingSlots: list[str] = Field(default_factory=list)
    duplicateFens: list[str] = Field(default_factory=list)
    coverageTargets: list[str] = Field(default_factory=list)


# Compatibility aliases for older names used by existing helpers/tests.
ChessValidatedExample = ChessBuiltExample
ChessValidatedExampleSet = ChessBuiltExampleSet
