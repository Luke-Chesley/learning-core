from __future__ import annotations

import json
import re
from typing import Any, Optional

import chess as chess_lib
from langchain_core.tools import tool

from learning_core.contracts.activity import ActivityArtifact
from learning_core.domain.chess_engine import apply_move, describe_position, legal_moves, normalize_move, validate_fen
from learning_core.skills.activity_generate.packs.chess.contracts import ChessBuiltExampleSet, ChessExamplePlan
from learning_core.skills.activity_generate.packs.chess.planning import (
    build_chess_example_set as build_engine_backed_example_set,
    render_chess_example_summary,
    validate_chess_artifact_against_example_set as validate_engine_backed_artifact,
    validate_chess_example_set as validate_engine_backed_example_set,
)

_WHITE_TO_MOVE = re.compile(r"\bwhite\s+to\s+move\b", re.IGNORECASE)
_BLACK_TO_MOVE = re.compile(r"\bblack\s+to\s+move\b", re.IGNORECASE)
_CHECK_CLAIM = re.compile(r"\b(?:is in check|king is in check|position is in check)\b", re.IGNORECASE)
_CHECKMATE_CLAIM = re.compile(r"\b(?:is checkmate|position is checkmate|already checkmate)\b", re.IGNORECASE)


def _serialize(payload: object) -> str:
    return json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True)


@tool
def chess_legal_moves(fen: str) -> str:
    """Return normalized legal moves for a chess position."""
    try:
        return _serialize({"legalMoves": legal_moves(fen)})
    except ValueError as error:
        return f"Error: {error}"


@tool
def chess_describe_position(fen: str) -> str:
    """Return engine facts for a chess position."""
    try:
        return _serialize(describe_position(fen))
    except ValueError as error:
        return f"Error: {error}"


@tool
def chess_apply_move(fen: str, move: str) -> str:
    """Apply a legal move to a chess position and return the resulting state."""
    try:
        return _serialize(apply_move(fen, move))
    except ValueError as error:
        return f"Error: {error}"


@tool
def chess_normalize_move(fen: str, move: str) -> str:
    """Normalize a SAN or UCI move against a chess position."""
    try:
        return _serialize(normalize_move(fen, move))
    except ValueError as error:
        return f"Error: {error}"


@tool
def chess_validate_widget_config(
    fen: str,
    expected_moves: Optional[list[str]] = None,
    highlight_squares: Optional[list[str]] = None,
    arrows: Optional[list[dict]] = None,
    prompt_text: Optional[str] = None,
) -> str:
    """Validate a chess board widget configuration against engine facts."""
    result: dict[str, Any] = {"valid": True, "errors": [], "warnings": []}

    try:
        normalized_fen = validate_fen(fen)
        result["normalizedFen"] = normalized_fen
    except ValueError as error:
        result["valid"] = False
        result["errors"].append(f"Invalid FEN: {error}")
        return _serialize(result)

    position = describe_position(normalized_fen)
    result["sideToMove"] = position["sideToMove"]
    result["isCheck"] = position["isCheck"]
    result["isCheckmate"] = position["isCheckmate"]
    result["isStalemate"] = position["isStalemate"]
    result["legalMoveCount"] = position["legalMoveCount"]

    if expected_moves:
        normalized_expected: list[dict[str, Any]] = []
        illegal_moves: list[str] = []
        for move_str in expected_moves:
            try:
                normalized_expected.append(normalize_move(normalized_fen, move_str))
            except ValueError:
                illegal_moves.append(move_str)
        result["normalizedExpectedMoves"] = normalized_expected
        if illegal_moves:
            result["valid"] = False
            result["illegalExpectedMoves"] = illegal_moves
            result["errors"].append(f"Illegal expected moves: {', '.join(illegal_moves)}")

    if highlight_squares:
        board = chess_lib.Board(normalized_fen)
        occupied = {chess_lib.square_name(square) for square in board.piece_map()}
        move_squares = set()
        for move in result.get("normalizedExpectedMoves", []):
            uci = move.get("uci", "")
            if len(uci) >= 4:
                move_squares.add(uci[:2])
                move_squares.add(uci[2:4])
        for square in highlight_squares:
            if square not in occupied and square not in move_squares:
                result["warnings"].append(f"Highlight '{square}' is not tied to a piece or expected move.")

    if arrows:
        board = chess_lib.Board(normalized_fen)
        occupied = {chess_lib.square_name(square) for square in board.piece_map()}
        for arrow in arrows:
            from_square = arrow.get("fromSquare", "")
            if from_square not in occupied:
                result["warnings"].append(f"Arrow from '{from_square}' starts on an empty square.")

    if prompt_text:
        side = position["sideToMove"]
        if _WHITE_TO_MOVE.search(prompt_text) and side != "white":
            result["valid"] = False
            result["errors"].append(f"Prompt says White to move but FEN is {side} to move.")
        if _BLACK_TO_MOVE.search(prompt_text) and side != "black":
            result["valid"] = False
            result["errors"].append(f"Prompt says Black to move but FEN is {side} to move.")
        if _CHECK_CLAIM.search(prompt_text) and not position["isCheck"]:
            result["valid"] = False
            result["errors"].append("Prompt claims the position is check, but it is not.")
        if _CHECKMATE_CLAIM.search(prompt_text) and not position["isCheckmate"]:
            result["valid"] = False
            result["errors"].append("Prompt claims the position is checkmate, but it is not.")

    return _serialize(result)


@tool
def chess_build_example_set(plan_json: str) -> str:
    """Build a validated chess example set from a structured plan JSON payload."""
    try:
        raw = json.loads(plan_json)
        plan = ChessExamplePlan.model_validate(raw.get("plan", raw))
        example_set = build_engine_backed_example_set(plan)
        return _serialize(example_set.model_dump(mode="json", exclude_none=True))
    except Exception as error:
        return f"Error: {error}"


@tool
def chess_validate_example_set(example_set_json: str) -> str:
    """Validate a chess example set for distinctness and concept coverage."""
    try:
        example_set = ChessBuiltExampleSet.model_validate(json.loads(example_set_json))
        return _serialize(validate_engine_backed_example_set(example_set).model_dump(mode="json", exclude_none=True))
    except Exception as error:
        return f"Error: {error}"


@tool
def chess_validate_final_activity(artifact_json: str, example_set_json: str) -> str:
    """Validate a final chess activity against a validated example set."""
    try:
        artifact = ActivityArtifact.model_validate(json.loads(artifact_json))
        example_set = ChessBuiltExampleSet.model_validate(json.loads(example_set_json))
        return _serialize(
            validate_engine_backed_artifact(artifact, example_set).model_dump(mode="json", exclude_none=True)
        )
    except Exception as error:
        return f"Error: {error}"


CHESS_TOOLS = [
    chess_legal_moves,
    chess_describe_position,
    chess_apply_move,
    chess_normalize_move,
    chess_validate_widget_config,
]

CHESS_PLANNING_TOOLS = [
    chess_build_example_set,
    chess_validate_example_set,
    chess_validate_final_activity,
]
