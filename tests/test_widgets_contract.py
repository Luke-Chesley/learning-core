import pytest

from learning_core.contracts.activity import ActivityArtifact
from learning_core.contracts.widgets import ChessBoardWidget, MathSymbolicWidget


def test_chess_widget_payload_validates():
    widget = ChessBoardWidget.model_validate(
        {
            "surfaceKind": "board_surface",
            "engineKind": "chess",
            "version": "1",
            "surface": {"orientation": "white"},
            "state": {"fen": "4k3/8/8/8/8/8/4Q3/4K3 w - - 0 1"},
            "interaction": {"mode": "move_input"},
            "evaluation": {"expectedMoves": ["Qb5+", "e2b5"]},
            "annotations": {
                "highlightSquares": ["e2"],
                "arrows": [{"fromSquare": "e2", "toSquare": "b5", "color": "green"}],
            },
        }
    )

    assert widget.engineKind == "chess"
    assert widget.state.fen.startswith("4k3")
    assert widget.display.boardRole == "primary"
    assert widget.feedback.displayMode == "inline"


def test_math_widget_payload_validates():
    widget = MathSymbolicWidget.model_validate(
        {
            "surfaceKind": "expression_surface",
            "engineKind": "math_symbolic",
            "version": "1",
            "surface": {"placeholder": "x = ?", "mathKeyboard": True},
            "state": {"promptLatex": "2x + 3 = 11", "initialValue": ""},
            "interaction": {"mode": "expression_entry"},
            "evaluation": {"expectedExpression": "x=4", "equivalenceMode": "equivalent"},
            "annotations": {"helperText": "Enter the solved equation."},
        }
    )

    assert widget.engineKind == "math_symbolic"


def test_activity_artifact_accepts_interactive_widget_component():
    artifact = ActivityArtifact.model_validate(
        {
            "schemaVersion": "2",
            "title": "Best move practice",
            "purpose": "Play the best move from the position.",
            "activityKind": "guided_practice",
            "linkedObjectiveIds": [],
            "linkedSkillTitles": ["best move"],
            "estimatedMinutes": 8,
            "interactionMode": "digital",
            "components": [
                {
                    "type": "interactive_widget",
                    "id": "best-move",
                    "prompt": "White to move. Find the best move.",
                    "required": True,
                    "widget": {
                        "surfaceKind": "board_surface",
                        "engineKind": "chess",
                        "version": "1",
                        "surface": {"orientation": "white"},
                        "state": {"fen": "4k3/8/8/8/8/8/4Q3/4K3 w - - 0 1"},
                        "interaction": {"mode": "move_input"},
                        "evaluation": {"expectedMoves": ["Qb5+", "e2b5"]},
                        "annotations": {"highlightSquares": [], "arrows": []},
                    },
                }
            ],
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

    assert artifact.components[0].type == "interactive_widget"


def test_activity_artifact_rejects_legacy_top_level_chess_component():
    with pytest.raises(Exception):
        ActivityArtifact.model_validate(
            {
                "schemaVersion": "2",
                "title": "Legacy chess board",
                "purpose": "Rejected legacy component.",
                "activityKind": "guided_practice",
                "linkedObjectiveIds": [],
                "linkedSkillTitles": ["best move"],
                "estimatedMinutes": 8,
                "interactionMode": "digital",
                "components": [
                    {
                        "type": "chess_board",
                        "id": "legacy",
                        "prompt": "Legacy board",
                        "fen": "4k3/8/8/8/8/8/4Q3/4K3 w - - 0 1",
                    }
                ],
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
