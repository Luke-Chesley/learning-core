from learning_core.contracts.activity import ActivityArtifact
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


def test_widget_validation_normalizes_chess_widget_without_errors():
    artifact = _activity_with_components(
        [
            {
                "type": "interactive_widget",
                "id": "best-move",
                "prompt": "White to move. Find the checking move.",
                "required": True,
                "widget": {
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
                },
            }
        ]
    )

    normalized, errors = normalize_and_validate_widget_activity(artifact)

    assert errors == []
    widget = normalized.components[0].widget
    assert widget.state.initialFen == widget.state.fen
    assert widget.evaluation.expectedMoves == ["e2b5"]


def test_widget_validation_rejects_primary_widget_that_is_not_first_interactive_component():
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

    _normalized, errors = normalize_and_validate_widget_activity(artifact)

    assert any("not the first interactive component" in error for error in errors)


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

    _normalized, errors = normalize_and_validate_widget_activity(artifact)

    assert any("must start from its initialFen" in error for error in errors)
    assert any("prompt claims the current position is check" in error for error in errors)
