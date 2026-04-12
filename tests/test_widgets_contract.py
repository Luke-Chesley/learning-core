import pytest

from learning_core.contracts.activity import ActivityArtifact
from learning_core.contracts.widgets import (
    ChessBoardWidget,
    GraphingWidget,
    MapGeoJsonWidget,
    MathSymbolicWidget,
    widget_accepts_input,
)


def test_chess_widget_payload_validates():
    widget = ChessBoardWidget.model_validate(
        {
            "surfaceKind": "board_surface",
            "engineKind": "chess",
            "version": "1",
            "instructionText": "Play the move directly on the board.",
            "caption": "Board work first, explanation second.",
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
    assert widget.state.initialFen == widget.state.fen
    assert widget.display.boardRole == "primary"
    assert widget.feedback.displayMode == "inline"
    assert widget.instructionText == "Play the move directly on the board."


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


def test_graph_widget_view_only_is_not_treated_as_input():
    widget = GraphingWidget.model_validate(
        {
            "surfaceKind": "graph_surface",
            "engineKind": "graphing",
            "version": "1",
            "surface": {"xLabel": "x", "yLabel": "y", "grid": True},
            "state": {"prompt": "Inspect the graph only.", "initialExpression": "y=x"},
            "interaction": {"mode": "view_only", "allowReset": False, "resetPolicy": "not_allowed"},
            "feedback": {"mode": "none", "displayMode": "inline"},
            "evaluation": {"expectedGraphDescription": "line with slope 1"},
            "annotations": {"overlayText": "Reference graph"},
        }
    )

    assert widget.display.surfaceRole == "primary"
    assert widget.interaction.allowReset is False
    assert widget_accepts_input(widget) is False


def test_map_widget_payload_validates():
    widget = MapGeoJsonWidget.model_validate(
        {
            "surfaceKind": "map_surface",
            "engineKind": "map_geojson",
            "version": "1",
            "instructionText": "Select South America.",
            "surface": {
                "projection": "equal_earth",
                "basemapStyle": "none",
                "center": {"lon": -120.0, "lat": 39.0},
                "zoom": 2.5,
            },
            "state": {
                "sourceId": "geoboundaries:USA:ADM1",
                "activeLayerIds": ["geoboundaries-usa-adm1-base"],
                "selectedFeatureIds": [],
                "markerCoordinate": None,
                "drawnPath": [],
                "labelAssignments": {},
                "timelineYear": None,
            },
            "interaction": {
                "mode": "select_region",
                "submissionMode": "explicit_submit",
                "selectionBehavior": "single",
            },
            "feedback": {"mode": "explicit_submit", "displayMode": "inline"},
            "layers": [
                {
                    "id": "geoboundaries-usa-adm1-base",
                    "sourceId": "geoboundaries:USA:ADM1",
                    "featureIds": ["california", "oregon"],
                    "labelField": "shapeName",
                    "visible": True,
                    "stylePreset": "political",
                }
            ],
            "evaluation": {
                "acceptedFeatureIds": ["california"],
                "featureSelectionMode": "exact",
                "requiredCount": 1,
                "minimumCoverage": 1.0,
            },
            "annotations": {
                "legendTitle": "World Regions Intro",
                "guidedPrompts": [],
                "callouts": [],
            },
        }
    )

    assert widget.engineKind == "map_geojson"
    assert widget.interaction.mode == "select_region"
    assert widget_accepts_input(widget) is True


def test_board_widget_coerces_inspect_to_view_only():
    widget = ChessBoardWidget.model_validate(
        {
            "surfaceKind": "board_surface",
            "engineKind": "chess",
            "version": "1",
            "surface": {"orientation": "white"},
            "state": {"fen": "4k3/8/8/8/8/8/4Q3/4K3 w - - 0 1"},
            "interaction": {"mode": "inspect"},
            "feedback": {"mode": "immediate", "displayMode": "inline"},
            "evaluation": {"expectedMoves": []},
            "annotations": {"highlightSquares": [], "arrows": []},
        }
    )

    assert widget.interaction.mode == "view_only"
    assert widget.feedback.mode == "none"


def test_view_only_board_coerces_feedback_to_none():
    widget = ChessBoardWidget.model_validate(
        {
            "surfaceKind": "board_surface",
            "engineKind": "chess",
            "version": "1",
            "surface": {"orientation": "white"},
            "state": {"fen": "4k3/8/8/8/8/8/4Q3/4K3 w - - 0 1"},
            "interaction": {"mode": "view_only"},
            "feedback": {"mode": "immediate", "displayMode": "inline"},
            "evaluation": {"expectedMoves": []},
            "annotations": {"highlightSquares": [], "arrows": []},
        }
    )

    assert widget.interaction.mode == "view_only"
    assert widget.feedback.mode == "none"


def test_widget_contract_rejects_single_attempt_with_reset_enabled():
    with pytest.raises(Exception):
        ChessBoardWidget.model_validate(
            {
                "surfaceKind": "board_surface",
                "engineKind": "chess",
                "version": "1",
                "surface": {"orientation": "white"},
                "state": {"fen": "4k3/8/8/8/8/8/4Q3/4K3 w - - 0 1"},
                "interaction": {
                    "mode": "move_input",
                    "allowReset": True,
                    "resetPolicy": "reset_to_initial",
                    "attemptPolicy": "single_attempt",
                },
                "evaluation": {"expectedMoves": ["Qb5+"]},
                "annotations": {"highlightSquares": [], "arrows": []},
            }
        )


def test_widget_contract_rejects_explicit_submit_feedback_without_explicit_submit_interaction():
    with pytest.raises(Exception):
        MathSymbolicWidget.model_validate(
            {
                "surfaceKind": "expression_surface",
                "engineKind": "math_symbolic",
                "version": "1",
                "surface": {"placeholder": "x = ?", "mathKeyboard": True},
                "state": {"promptLatex": "2x + 3 = 11", "initialValue": ""},
                "interaction": {"mode": "expression_entry", "submissionMode": "immediate"},
                "feedback": {"mode": "explicit_submit", "displayMode": "inline"},
                "evaluation": {"expectedExpression": "x=4", "equivalenceMode": "equivalent"},
                "annotations": {"helperText": "Enter the solved equation."},
            }
        )


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
