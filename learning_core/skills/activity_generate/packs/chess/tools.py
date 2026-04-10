from __future__ import annotations

import json

from langchain_core.tools import tool

from learning_core.domain.chess_engine import apply_move, describe_position, legal_moves, normalize_move


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


CHESS_TOOLS = [chess_legal_moves, chess_describe_position, chess_apply_move, chess_normalize_move]
