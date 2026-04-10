from __future__ import annotations

from collections import Counter
from typing import Any

import chess


def _board(fen: str) -> chess.Board:
    normalized = fen.strip()
    if not normalized:
        raise ValueError("FEN is required.")
    try:
        return chess.Board(normalized)
    except ValueError as error:
        raise ValueError(f"Invalid FEN: {error}") from error


def _promotion_symbol(piece_type: int | None) -> str | None:
    if piece_type is None:
        return None
    return chess.piece_symbol(piece_type)


def _move_dict(board: chess.Board, move: chess.Move) -> dict[str, Any]:
    return {
        "uci": move.uci(),
        "san": board.san(move),
        "from": chess.square_name(move.from_square),
        "to": chess.square_name(move.to_square),
        "promotion": _promotion_symbol(move.promotion),
    }


def _candidate_strings(move: Any) -> list[str]:
    candidates: list[str] = []
    if isinstance(move, str) and move.strip():
        candidates.append(move.strip())
    elif isinstance(move, dict):
        for key in ("uci", "san", "move", "lan"):
            value = move.get(key)
            if isinstance(value, str) and value.strip():
                candidates.append(value.strip())
        from_square = move.get("from")
        to_square = move.get("to")
        promotion = move.get("promotion")
        if isinstance(from_square, str) and isinstance(to_square, str):
            uci = from_square.strip().lower() + to_square.strip().lower()
            if isinstance(promotion, str) and promotion.strip():
                uci += promotion.strip().lower()
            candidates.append(uci)
    return candidates


def _parse_move(board: chess.Board, move: Any) -> chess.Move:
    for candidate in _candidate_strings(move):
        try:
            parsed = chess.Move.from_uci(candidate.lower())
        except ValueError:
            parsed = None
        if parsed is not None and parsed in board.legal_moves:
            return parsed

        try:
            parsed = board.parse_san(candidate)
        except ValueError:
            parsed = None
        if parsed is not None and parsed in board.legal_moves:
            return parsed

    raise ValueError("Move is not legal in the provided position.")


def validate_fen(fen: str) -> str:
    return _board(fen).fen()


def legal_moves(fen: str) -> list[dict[str, Any]]:
    board = _board(fen)
    return [_move_dict(board, move) for move in board.legal_moves]


def normalize_move(fen: str, move: Any) -> dict[str, Any]:
    board = _board(fen)
    return _move_dict(board, _parse_move(board, move))


def apply_move(fen: str, move: Any) -> dict[str, Any]:
    board = _board(fen)
    parsed = _parse_move(board, move)
    normalized_move = _move_dict(board, parsed)
    board.push(parsed)
    return {
        "inputFen": fen.strip(),
        "normalizedMove": normalized_move,
        "fenAfter": board.fen(),
        "sideToMove": "white" if board.turn == chess.WHITE else "black",
        "isCheck": board.is_check(),
        "isCheckmate": board.is_checkmate(),
        "isStalemate": board.is_stalemate(),
    }


def evaluate_move(fen: str, move: Any, expected_moves: list[str]) -> dict[str, Any]:
    board = _board(fen)
    normalized_learner_move = _move_dict(board, _parse_move(board, move))
    normalized_expected_moves = []
    for expected_move in expected_moves:
        expected_board = _board(fen)
        normalized_expected_moves.append(_move_dict(expected_board, _parse_move(expected_board, expected_move)))

    expected_uci = {item["uci"] for item in normalized_expected_moves}
    is_correct = normalized_learner_move["uci"] in expected_uci

    return {
        "status": "correct" if is_correct else "incorrect",
        "learnerMove": normalized_learner_move,
        "expectedMoves": normalized_expected_moves,
    }


def describe_position(fen: str) -> dict[str, Any]:
    board = _board(fen)
    piece_counts = {
        "white": dict(
            Counter(piece.symbol().upper() for piece in board.piece_map().values() if piece.color == chess.WHITE)
        ),
        "black": dict(
            Counter(piece.symbol().lower() for piece in board.piece_map().values() if piece.color == chess.BLACK)
        ),
    }

    return {
        "fen": board.fen(),
        "sideToMove": "white" if board.turn == chess.WHITE else "black",
        "legalMoveCount": board.legal_moves.count(),
        "isCheck": board.is_check(),
        "isCheckmate": board.is_checkmate(),
        "isStalemate": board.is_stalemate(),
        "fullmoveNumber": board.fullmove_number,
        "pieceSummary": piece_counts,
    }


def board_annotations(
    *,
    highlight_squares: list[str] | None = None,
    arrows: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    highlights = [square.strip().lower() for square in (highlight_squares or []) if square.strip()]
    normalized_arrows = []
    for arrow in arrows or []:
        normalized_arrows.append(
            {
                "fromSquare": str(arrow["fromSquare"]).strip().lower(),
                "toSquare": str(arrow["toSquare"]).strip().lower(),
                "color": str(arrow.get("color", "green")).strip().lower(),
            }
        )
    return {
        "highlightSquares": highlights,
        "arrows": normalized_arrows,
    }
