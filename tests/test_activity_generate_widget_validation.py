from learning_core.contracts.activity import ActivityArtifact
from learning_core.skills.activity_generate.packs.chess.pack import ChessPack
from learning_core.skills.activity_generate.packs.chess.validation import ChessValidator
from learning_core.skills.activity_generate.validation.widgets import normalize_and_validate_widget_activity


def _activity_with_components(components):
    return ActivityArtifact.model_validate(
        {
            "schemaVersion": "2",
            "title": "Chess move practice",
            "purpose": "Use the board as the main evidence and submit the move.",
            "activityKind": "guided_practice",
            "linkedObjectiveIds": [],
            "linkedSkillTitles": ["best move"],
            "estimatedMinutes": 8,
            "interactionMode": "digital",
            "components": components,
            "completionRules": {"strategy": "all_interactive_components"},
            "evidenceSchema": {
                "captureKinds": ["answer_response"],
                "requiresReview": False,
                "autoScorable": True,
            },
            "scoringModel": {
                "mode": "correctness_based",
                "masteryThreshold": 0.8,
                "reviewThreshold": 0.6,
            },
        }
    )


_VALID_CHESS_WIDGET = {
    "surfaceKind": "board_surface",
    "engineKind": "chess",
    "version": "1",
    "instructionText": "Play the move on the board.",
    "caption": "The board is the main evidence.",
    "surface": {"orientation": "white"},
    "state": {"fen": "4k3/8/8/8/8/8/4Q3/4K3 w - - 0 1"},
    "display": {
        "showSideToMove": True,
        "showCoordinates": True,
        "showMoveHint": True,
        "boardRole": "primary",
    },
    "interaction": {
        "mode": "move_input",
        "submissionMode": "immediate",
        "selectionMode": "click_click",
        "showLegalTargets": True,
        "allowReset": True,
        "resetPolicy": "reset_to_initial",
        "attemptPolicy": "allow_retry",
    },
    "feedback": {"mode": "immediate", "displayMode": "inline"},
    "evaluation": {"expectedMoves": ["Qb5+", "e2b5"]},
    "annotations": {"highlightSquares": ["e2"], "arrows": []},
}


def test_widget_validation_normalizes_chess_widget_without_errors():
    artifact = _activity_with_components(
        [
            {
                "type": "interactive_widget",
                "id": "best-move",
                "prompt": "White to move. Find the checking move.",
                "required": True,
                "widget": _VALID_CHESS_WIDGET,
            }
        ]
    )

    chess_pack = ChessPack()
    normalized, hard_errors, soft_warnings = normalize_and_validate_widget_activity(artifact, [chess_pack])

    assert hard_errors == []
    assert soft_warnings == []
    widget = normalized.components[0].widget
    assert widget.state.initialFen == widget.state.fen
    assert widget.evaluation.expectedMoves == ["e2b5"]


def test_widget_validation_accepts_secondary_board_role_alias():
    artifact = _activity_with_components(
        [
            {
                "type": "interactive_widget",
                "id": "best-move",
                "prompt": "White to move. Find the checking move.",
                "required": True,
                "widget": {
                    **_VALID_CHESS_WIDGET,
                    "display": {
                        "showSideToMove": True,
                        "showCoordinates": True,
                        "showMoveHint": True,
                        "boardRole": "secondary",
                    },
                },
            }
        ]
    )

    chess_pack = ChessPack()
    normalized, hard_errors, soft_warnings = normalize_and_validate_widget_activity(artifact, [chess_pack])

    assert hard_errors == []
    assert normalized.components[0].widget.display.boardRole == "supporting"
    assert any("board-centered" in warning or "move input" in warning for warning in soft_warnings)


def test_primary_widget_not_first_interactive_is_soft_warning():
    """Primary widget not being the first interactive component should be a soft warning, not a hard error."""
    artifact = _activity_with_components(
        [
            {
                "type": "short_answer",
                "id": "warm-up",
                "prompt": "Name a forcing move.",
                "required": True,
            },
            {
                "type": "interactive_widget",
                "id": "best-move",
                "prompt": "White to move. Find the checking move.",
                "required": True,
                "widget": {
                    "surfaceKind": "board_surface",
                    "engineKind": "chess",
                    "version": "1",
                    "surface": {"orientation": "white"},
                    "state": {"fen": "4k3/8/8/8/8/8/4Q3/4K3 w - - 0 1"},
                    "display": {"boardRole": "primary"},
                    "interaction": {"mode": "move_input"},
                    "feedback": {"mode": "immediate", "displayMode": "inline"},
                    "evaluation": {"expectedMoves": ["Qb5+"]},
                    "annotations": {"highlightSquares": [], "arrows": []},
                },
            },
        ]
    )

    chess_pack = ChessPack()
    _normalized, hard_errors, soft_warnings = normalize_and_validate_widget_activity(artifact, [chess_pack])

    assert not any("not the first interactive component" in error for error in hard_errors)
    assert any("not the first interactive component" in warning for warning in soft_warnings)


def test_widget_validation_rejects_board_claims_that_contradict_state():
    artifact = _activity_with_components(
        [
            {
                "type": "interactive_widget",
                "id": "bad-board",
                "prompt": "White to move. The king is in check.",
                "required": True,
                "widget": {
                    "surfaceKind": "board_surface",
                    "engineKind": "chess",
                    "version": "1",
                    "surface": {"orientation": "white"},
                    "state": {
                        "fen": "4k3/8/8/8/8/8/4Q3/4K3 w - - 0 1",
                        "initialFen": "4k3/8/8/1Q6/8/8/8/4K3 b - - 1 1",
                    },
                    "display": {"showSideToMove": False, "boardRole": "primary"},
                    "interaction": {"mode": "move_input"},
                    "feedback": {"mode": "immediate", "displayMode": "inline"},
                    "evaluation": {"expectedMoves": ["Qb5+"]},
                    "annotations": {"highlightSquares": [], "arrows": []},
                },
            }
        ]
    )

    chess_pack = ChessPack()
    _normalized, hard_errors, _soft_warnings = normalize_and_validate_widget_activity(artifact, [chess_pack])

    assert any("must start from its initialFen" in error for error in hard_errors)
    assert any("prompt claims the current position is check" in error for error in hard_errors)


def test_chess_validators_live_under_chess_pack():
    """Chess-specific validation must come from the chess pack, not base validation."""
    chess_pack = ChessPack()
    validators = chess_pack.validators()
    assert len(validators) == 1
    assert isinstance(validators[0], ChessValidator)


def test_chess_pack_auto_injects_correct_ui_specs():
    chess_pack = ChessPack()
    specs = chess_pack.auto_injected_ui_specs()
    assert "ui_components/interactive_widget.md" in specs
    assert "ui_widgets/board_surface__chess.md" in specs


def test_illegal_expected_moves_hard_fail():
    """Illegal expected moves must be a hard error."""
    artifact = _activity_with_components(
        [
            {
                "type": "interactive_widget",
                "id": "bad-moves",
                "prompt": "White to move. Find the best move.",
                "required": True,
                "widget": {
                    "surfaceKind": "board_surface",
                    "engineKind": "chess",
                    "version": "1",
                    "surface": {"orientation": "white"},
                    "state": {"fen": "4k3/8/8/8/8/8/4Q3/4K3 w - - 0 1"},
                    "display": {"showSideToMove": True, "boardRole": "primary"},
                    "interaction": {"mode": "move_input"},
                    "feedback": {"mode": "immediate", "displayMode": "inline"},
                    "evaluation": {"expectedMoves": ["Nf3"]},
                    "annotations": {"highlightSquares": [], "arrows": []},
                },
            }
        ]
    )

    chess_pack = ChessPack()
    _normalized, hard_errors, _soft_warnings = normalize_and_validate_widget_activity(artifact, [chess_pack])

    assert any("invalid chess state" in error for error in hard_errors)


def test_multiple_primary_widgets_in_drill_pattern_allowed():
    """Multiple primary widgets in a repeated drill pattern should not hard fail."""
    artifact = _activity_with_components(
        [
            {
                "type": "interactive_widget",
                "id": "puzzle-1",
                "prompt": "White to move. Find the checking move.",
                "required": True,
                "widget": {**_VALID_CHESS_WIDGET},
            },
            {
                "type": "single_select",
                "id": "classify-1",
                "prompt": "What type of tactic was that?",
                "choices": [
                    {"id": "a", "text": "Fork", "correct": True},
                    {"id": "b", "text": "Pin"},
                ],
                "required": True,
            },
            {
                "type": "interactive_widget",
                "id": "puzzle-2",
                "prompt": "White to move. Find the checking move.",
                "required": True,
                "widget": {**_VALID_CHESS_WIDGET},
            },
            {
                "type": "single_select",
                "id": "classify-2",
                "prompt": "What type of tactic was that?",
                "choices": [
                    {"id": "a", "text": "Fork"},
                    {"id": "b", "text": "Skewer", "correct": True},
                ],
                "required": True,
            },
        ]
    )

    chess_pack = ChessPack()
    _normalized, hard_errors, soft_warnings = normalize_and_validate_widget_activity(artifact, [chess_pack])

    assert not any("primary" in error and "first interactive" in error for error in hard_errors)


def test_base_skill_no_chess_pack_no_chess_validators():
    """Without the chess pack active, no chess-specific validation runs."""
    artifact = _activity_with_components(
        [
            {
                "type": "interactive_widget",
                "id": "board",
                "prompt": "White to move.",
                "required": True,
                "widget": {
                    "surfaceKind": "board_surface",
                    "engineKind": "chess",
                    "version": "1",
                    "surface": {"orientation": "white"},
                    "state": {"fen": "4k3/8/8/8/8/8/4Q3/4K3 w - - 0 1"},
                    "display": {"showSideToMove": True, "boardRole": "primary"},
                    "interaction": {"mode": "move_input"},
                    "feedback": {"mode": "immediate", "displayMode": "inline"},
                    "evaluation": {"expectedMoves": ["Qb5+"]},
                    "annotations": {"highlightSquares": [], "arrows": []},
                },
            }
        ]
    )

    # No active packs
    _normalized, hard_errors, soft_warnings = normalize_and_validate_widget_activity(artifact, active_packs=[])

    # Base validation runs but chess-specific checks do not
    assert not any("chess" in error.lower() for error in hard_errors)


def test_chess_pack_detect_pack_widgets():
    chess_pack = ChessPack()
    artifact = _activity_with_components(
        [
            {
                "type": "interactive_widget",
                "id": "board-1",
                "prompt": "White to move.",
                "required": True,
                "widget": {**_VALID_CHESS_WIDGET},
            },
            {
                "type": "short_answer",
                "id": "explain",
                "prompt": "Why is this the best move?",
                "required": True,
            },
        ]
    )

    widget_ids = chess_pack.detect_pack_widgets(artifact)
    assert widget_ids == ["board-1"]


def test_chess_pack_required_tool_names():
    chess_pack = ChessPack()
    required = chess_pack.required_tool_names()
    assert "chess_validate_widget_config" in required


def test_move_input_not_primary_is_soft_warning():
    """move_input with non-primary boardRole should be a soft warning, not hard error."""
    artifact = _activity_with_components(
        [
            {
                "type": "interactive_widget",
                "id": "board",
                "prompt": "White to move. Find the best move.",
                "required": True,
                "widget": {
                    "surfaceKind": "board_surface",
                    "engineKind": "chess",
                    "version": "1",
                    "surface": {"orientation": "white"},
                    "state": {"fen": "4k3/8/8/8/8/8/4Q3/4K3 w - - 0 1"},
                    "display": {"showSideToMove": True, "boardRole": "supporting"},
                    "interaction": {"mode": "move_input"},
                    "feedback": {"mode": "immediate", "displayMode": "inline"},
                    "evaluation": {"expectedMoves": ["Qb5+"]},
                    "annotations": {"highlightSquares": [], "arrows": []},
                },
            }
        ]
    )

    chess_pack = ChessPack()
    _normalized, hard_errors, soft_warnings = normalize_and_validate_widget_activity(artifact, [chess_pack])

    assert not any("boardRole" in error for error in hard_errors)
    assert any("move input" in warning and "not" in warning and "primary" in warning for warning in soft_warnings)
