from __future__ import annotations

import re

import chess

from learning_core.contracts.activity import ActivityArtifact, InteractiveWidgetComponent
from learning_core.contracts.widgets import ChessBoardWidget
from learning_core.domain.chess_engine import describe_position, normalize_move, validate_fen

_WHITE_TO_MOVE_PATTERN = re.compile(r"\bwhite\s+to\s+move\b", re.IGNORECASE)
_BLACK_TO_MOVE_PATTERN = re.compile(r"\bblack\s+to\s+move\b", re.IGNORECASE)
_CURRENT_CHECK_PATTERNS = (
    re.compile(r"\bis in check\b", re.IGNORECASE),
    re.compile(r"\bposition is in check\b", re.IGNORECASE),
    re.compile(r"\bking is in check\b", re.IGNORECASE),
)
_CURRENT_CHECKMATE_PATTERNS = (
    re.compile(r"\bis checkmate\b", re.IGNORECASE),
    re.compile(r"\bposition is checkmate\b", re.IGNORECASE),
    re.compile(r"\balready checkmate\b", re.IGNORECASE),
)
_POSITION_CENTERED_PATTERNS = (
    re.compile(r"\bbest move\b", re.IGNORECASE),
    re.compile(r"\bfind (?:the )?(?:best|winning|forcing|checking) move\b", re.IGNORECASE),
    re.compile(r"\bplay (?:the )?(?:best|winning|forcing|checking) move\b", re.IGNORECASE),
    re.compile(r"\bfrom the position\b", re.IGNORECASE),
    re.compile(r"\buse the board\b", re.IGNORECASE),
    re.compile(r"\bside to move\b", re.IGNORECASE),
)


def _occupied_squares(fen: str) -> set[str]:
    board = chess.Board(fen)
    return {chess.square_name(square) for square in board.piece_map()}


def _all_visible_text(component: InteractiveWidgetComponent, widget: ChessBoardWidget) -> str:
    return " ".join(
        value.strip()
        for value in [component.prompt or "", widget.instructionText or "", widget.caption or ""]
        if value and value.strip()
    )


def _activity_context_text(artifact: ActivityArtifact, component: InteractiveWidgetComponent, widget: ChessBoardWidget) -> str:
    pieces = [
        artifact.title,
        artifact.purpose or "",
        " ".join(artifact.linkedSkillTitles),
        _all_visible_text(component, widget),
    ]
    return " ".join(value.strip() for value in pieces if value and value.strip())


def _legal_targets_by_source(fen: str) -> dict[str, set[str]]:
    board = chess.Board(fen)
    targets: dict[str, set[str]] = {}
    for move in board.legal_moves:
        from_square = chess.square_name(move.from_square)
        targets.setdefault(from_square, set()).add(chess.square_name(move.to_square))
    return targets


def normalize_chess_widget(widget: ChessBoardWidget) -> ChessBoardWidget:
    normalized = widget.model_copy(deep=True)
    normalized.state.fen = validate_fen(widget.state.fen)
    normalized.state.initialFen = validate_fen(widget.state.initialFen or widget.state.fen)

    deduped_moves: list[str] = []
    for move in widget.evaluation.expectedMoves:
        normalized_move = normalize_move(normalized.state.fen, move)["uci"]
        if normalized_move not in deduped_moves:
            deduped_moves.append(normalized_move)
    normalized.evaluation.expectedMoves = deduped_moves
    return normalized


def validate_chess_widget(
    artifact: ActivityArtifact,
    component: InteractiveWidgetComponent,
    widget: ChessBoardWidget,
) -> list[str]:
    errors: list[str] = []
    prompt = _all_visible_text(component, widget)
    activity_text = _activity_context_text(artifact, component, widget)
    position = describe_position(widget.state.fen)
    occupied_squares = _occupied_squares(widget.state.fen)
    legal_targets_by_source = _legal_targets_by_source(widget.state.fen)
    side_to_move = position["sideToMove"]
    expected_move_sources = {normalized_move[:2] for normalized_move in widget.evaluation.expectedMoves}
    expected_move_targets = {
        normalized_move[2:4] for normalized_move in widget.evaluation.expectedMoves if len(normalized_move) >= 4
    }

    if widget.state.initialFen != widget.state.fen:
        errors.append(
            f'Interactive widget "{component.id}" must start from its initialFen. Generated widgets should not begin mid-transition.'
        )

    if widget.interaction.mode == "move_input" and not widget.evaluation.expectedMoves:
        errors.append(
            f'Interactive widget "{component.id}" expects move input but has no evaluation.expectedMoves.'
        )

    if widget.interaction.mode == "view_only" and widget.evaluation.expectedMoves:
        errors.append(
            f'Interactive widget "{component.id}" is view_only but still includes evaluation.expectedMoves.'
        )

    if widget.interaction.mode == "move_input" and widget.display.boardRole != "primary":
        errors.append(
            f'Interactive widget "{component.id}" is a board-centered chess lesson with move input, so display.boardRole must be "primary".'
        )

    if any(pattern.search(activity_text) for pattern in _POSITION_CENTERED_PATTERNS):
        if widget.display.boardRole != "primary":
            errors.append(
                f'Interactive widget "{component.id}" appears in a board-centered chess lesson but is not marked primary.'
            )
        if widget.interaction.mode != "move_input":
            errors.append(
                f'Interactive widget "{component.id}" appears in a board-centered chess lesson but does not accept move input.'
            )

    has_white_to_move = _WHITE_TO_MOVE_PATTERN.search(prompt) is not None
    has_black_to_move = _BLACK_TO_MOVE_PATTERN.search(prompt) is not None
    if has_white_to_move and side_to_move != "white":
        errors.append(
            f'Interactive widget "{component.id}" prompt says White to move but the FEN is {side_to_move} to move.'
        )
    if has_black_to_move and side_to_move != "black":
        errors.append(
            f'Interactive widget "{component.id}" prompt says Black to move but the FEN is {side_to_move} to move.'
        )
    if not widget.display.showSideToMove and not has_white_to_move and not has_black_to_move:
        errors.append(
            f'Interactive widget "{component.id}" must make side to move clear in display or prompt.'
        )

    if any(pattern.search(prompt) for pattern in _CURRENT_CHECK_PATTERNS) and not position["isCheck"]:
        errors.append(
            f'Interactive widget "{component.id}" prompt claims the current position is check, but the FEN is not check.'
        )

    if any(pattern.search(prompt) for pattern in _CURRENT_CHECKMATE_PATTERNS) and not position["isCheckmate"]:
        errors.append(
            f'Interactive widget "{component.id}" prompt claims the current position is checkmate, but the FEN is not checkmate.'
        )

    for square in widget.annotations.highlightSquares:
        if square not in occupied_squares and square not in expected_move_sources | expected_move_targets:
            errors.append(
                f'Interactive widget "{component.id}" highlights "{square}" without tying it to a piece or expected move.'
            )

    for arrow in widget.annotations.arrows:
        if arrow.fromSquare not in occupied_squares:
            errors.append(
                f'Interactive widget "{component.id}" has an arrow starting from empty square "{arrow.fromSquare}".'
            )
            continue

        legal_targets = legal_targets_by_source.get(arrow.fromSquare, set())
        if arrow.toSquare not in legal_targets and arrow.toSquare not in expected_move_targets and arrow.toSquare not in occupied_squares:
            errors.append(
                f'Interactive widget "{component.id}" has an arrow to "{arrow.toSquare}" that is not a legal target, occupied square, or expected-move target.'
            )

    return errors
