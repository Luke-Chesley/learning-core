import pytest

from learning_core.domain.chess_engine import (
    apply_move,
    describe_position,
    evaluate_move,
    legal_moves,
    legal_targets,
    normalize_expected_moves,
    validate_fen,
)


def test_validate_fen_accepts_valid_position():
    normalized = validate_fen("4k3/8/8/8/8/8/4Q3/4K3 w - - 0 1")
    assert normalized == "4k3/8/8/8/8/8/4Q3/4K3 w - - 0 1"


def test_validate_fen_rejects_invalid_position():
    with pytest.raises(ValueError):
        validate_fen("not-a-fen")


def test_legal_moves_returns_normalized_moves():
    moves = legal_moves("4k3/8/8/8/8/8/4Q3/4K3 w - - 0 1")
    assert any(move["uci"] == "e2b5" for move in moves)
    assert any(move["san"] == "Qb5+" for move in moves)


def test_legal_targets_returns_targets_for_a_source_square():
    targets = legal_targets("4k3/8/8/8/8/8/4Q3/4K3 w - - 0 1", "e2")
    assert "b5" in targets
    assert "e8" in targets


def test_normalize_expected_moves_dedupes_equivalent_inputs():
    normalized = normalize_expected_moves(
        "4k3/8/8/8/8/8/4Q3/4K3 w - - 0 1",
        ["Qb5+", "e2b5"],
    )
    assert [move["uci"] for move in normalized] == ["e2b5"]


def test_apply_move_returns_next_position():
    result = apply_move("4k3/8/8/8/8/8/4Q3/4K3 w - - 0 1", "Qb5+")
    assert result["normalizedMove"]["uci"] == "e2b5"
    assert result["isCheck"] is True


def test_evaluate_move_matches_expected_moves():
    result = evaluate_move(
        "4k3/8/8/8/8/8/4Q3/4K3 w - - 0 1",
        {"from": "e2", "to": "b5", "uci": "e2b5"},
        ["Qb5+", "e2b5"],
    )
    assert result["status"] == "correct"


def test_describe_position_returns_compact_summary():
    summary = describe_position("4k3/8/8/8/8/8/4Q3/4K3 w - - 0 1")
    assert summary["sideToMove"] == "white"
    assert summary["legalMoveCount"] > 0
