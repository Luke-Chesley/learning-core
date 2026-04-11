from __future__ import annotations

import json
import re
from typing import Optional

from langchain_core.tools import tool

from learning_core.domain.chess_engine import apply_move, describe_position, legal_moves, normalize_move, validate_fen

_WHITE_TO_MOVE = re.compile(r"\bwhite\s+to\s+move\b", re.IGNORECASE)
_BLACK_TO_MOVE = re.compile(r"\bblack\s+to\s+move\b", re.IGNORECASE)
_CHECK_CLAIM = re.compile(r"\b(?:is in check|king is in check|position is in check)\b", re.IGNORECASE)
_CHECKMATE_CLAIM = re.compile(r"\b(?:is checkmate|position is checkmate|already checkmate)\b", re.IGNORECASE)


def _serialize(payload: object) -> str:
    return json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True)


@tool
def chess_legal_moves(fen: str) -> str:
    """Return normalized legal chess moves for a FEN position."""
    try:
        return _serialize({"legalMoves": legal_moves(fen)})
    except ValueError as error:
        return f"Error: {error}"


@tool
def chess_describe_position(fen: str) -> str:
    """Return a compact chess position summary for a FEN position."""
    try:
        return _serialize(describe_position(fen))
    except ValueError as error:
        return f"Error: {error}"


@tool
def chess_apply_move(fen: str, move: str) -> str:
    """Apply a legal move to a FEN position and return the resulting state."""
    try:
        return _serialize(apply_move(fen, move))
    except ValueError as error:
        return f"Error: {error}"


@tool
def chess_normalize_move(fen: str, move: str) -> str:
    """Normalize a SAN or UCI move against a FEN position."""
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
    """Validate a chess widget configuration and return structured validation results.

    Use this tool before finalizing any chess board widget to catch semantic issues.
    Pass the widget's FEN, expectedMoves, annotations, and any prompt text that makes
    claims about the position (e.g. "White to move", "the king is in check").

    Returns normalized FEN, side to move, position status, normalized expected moves,
    illegal moves, annotation issues, and any contradictions between prompt claims and
    engine facts.
    """
    result: dict = {"valid": True, "errors": [], "warnings": []}

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
        normalized_expected: list[dict] = []
        illegal_moves: list[str] = []
        for move_str in expected_moves:
            try:
                normalized = normalize_move(normalized_fen, move_str)
                normalized_expected.append(normalized)
            except ValueError:
                illegal_moves.append(move_str)
        result["normalizedExpectedMoves"] = normalized_expected
        if illegal_moves:
            result["valid"] = False
            result["illegalExpectedMoves"] = illegal_moves
            result["errors"].append(f"Illegal expected moves: {', '.join(illegal_moves)}")

    if highlight_squares:
        import chess as chess_lib
        board = chess_lib.Board(normalized_fen)
        occupied = {chess_lib.square_name(sq) for sq in board.piece_map()}
        move_squares = set()
        if expected_moves:
            for m in result.get("normalizedExpectedMoves", []):
                uci = m.get("uci", "")
                if len(uci) >= 4:
                    move_squares.add(uci[:2])
                    move_squares.add(uci[2:4])
        for sq in highlight_squares:
            if sq not in occupied and sq not in move_squares:
                result["warnings"].append(f"Highlight '{sq}' is not tied to a piece or expected move.")

    if arrows:
        import chess as chess_lib
        board = chess_lib.Board(normalized_fen)
        occupied = {chess_lib.square_name(sq) for sq in board.piece_map()}
        for arrow in arrows:
            from_sq = arrow.get("fromSquare", "")
            if from_sq not in occupied:
                result["warnings"].append(f"Arrow from '{from_sq}' starts on an empty square.")

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


CHESS_TOOLS = [chess_legal_moves, chess_describe_position, chess_apply_move, chess_normalize_move, chess_validate_widget_config]
