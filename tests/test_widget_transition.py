from learning_core.runtime.engine import AgentEngine
from learning_core.skills.catalog import build_skill_registry


_CHESS_WIDGET = {
    "surfaceKind": "board_surface",
    "engineKind": "chess",
    "version": "1",
    "instructionText": "Play the move on the board.",
    "caption": "Use the board as the main evidence.",
    "surface": {"orientation": "white"},
    "display": {
        "showSideToMove": True,
        "showCoordinates": True,
        "showMoveHint": True,
        "boardRole": "primary",
    },
    "state": {
        "fen": "4k3/8/8/8/8/8/4Q3/4K3 w - - 0 1",
        "initialFen": "4k3/8/8/8/8/8/4Q3/4K3 w - - 0 1",
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
    "annotations": {"highlightSquares": [], "arrows": []},
}


def _transition_envelope(learner_action, current_response=None):
    return {
        "input": {
            "activityId": "activity-1",
            "componentId": "best-move",
            "componentType": "interactive_widget",
            "widget": _CHESS_WIDGET,
            "learnerAction": learner_action,
            "currentResponse": current_response,
            "attemptMetadata": {
                "attemptId": "attempt-1",
                "source": "component_action",
            },
        },
        "app_context": {
            "product": "homeschool-v2",
            "surface": "learner_activity",
        },
    }


def test_widget_transition_select_square_returns_legal_targets():
    engine = AgentEngine(build_skill_registry())
    result = engine.execute(
        "widget_transition",
        _transition_envelope({"type": "select_square", "square": "e2"}),
    )

    assert result.artifact["accepted"] is True
    assert "b5" in result.artifact["legalTargets"]
    assert result.artifact["canonicalWidget"]["state"]["fen"].startswith("4k3")


def test_widget_transition_submit_move_returns_canonical_next_state_and_feedback():
    engine = AgentEngine(build_skill_registry())
    result = engine.execute(
        "widget_transition",
        _transition_envelope(
            {
                "type": "submit_move",
                "move": {"fromSquare": "e2", "toSquare": "b5", "promotion": "q"},
            }
        ),
    )

    assert result.artifact["accepted"] is True
    assert result.artifact["nextResponse"]["uci"] == "e2b5"
    assert result.artifact["canonicalWidget"]["state"]["fen"].startswith("4k3/8/8/1Q6")
    assert result.artifact["immediateFeedback"]["status"] == "correct"
    assert result.artifact["immediateFeedback"]["allowRetry"] is False


def test_widget_transition_wrong_legal_move_keeps_retryable_board_at_initial_state():
    engine = AgentEngine(build_skill_registry())
    result = engine.execute(
        "widget_transition",
        _transition_envelope(
            {
                "type": "submit_move",
                "move": {"fromSquare": "e2", "toSquare": "e4"},
            }
        ),
    )

    assert result.artifact["accepted"] is True
    assert result.artifact["normalizedLearnerAction"]["uci"] == "e2e4"
    assert result.artifact.get("nextResponse") is None
    assert result.artifact["canonicalWidget"]["state"]["fen"] == _CHESS_WIDGET["state"]["initialFen"]
    assert result.artifact["immediateFeedback"]["status"] == "incorrect"
    assert result.artifact["immediateFeedback"]["allowRetry"] is True


def test_widget_transition_invalid_move_returns_backend_legal_targets():
    engine = AgentEngine(build_skill_registry())
    result = engine.execute(
        "widget_transition",
        _transition_envelope(
            {
                "type": "submit_move",
                "move": {"fromSquare": "e2", "toSquare": "e1"},
            }
        ),
    )

    assert result.artifact["accepted"] is False
    assert "b5" in result.artifact["legalTargets"]
    assert result.artifact["errorMessage"] == "Move is not legal in the provided position."


def test_widget_transition_reset_returns_initial_state():
    engine = AgentEngine(build_skill_registry())
    result = engine.execute(
        "widget_transition",
        _transition_envelope({"type": "reset"}),
    )

    assert result.artifact["accepted"] is True
    assert result.artifact.get("nextResponse") is None
    assert result.artifact["canonicalWidget"]["state"]["fen"] == _CHESS_WIDGET["state"]["initialFen"]


def test_widget_transition_reset_uses_initial_fen_after_board_has_progressed():
    progressed_widget = {
        **_CHESS_WIDGET,
        "state": {
            "fen": "4k3/8/8/1Q6/8/8/8/4K3 b - - 1 1",
            "initialFen": _CHESS_WIDGET["state"]["initialFen"],
        },
    }
    engine = AgentEngine(build_skill_registry())
    result = engine.execute(
        "widget_transition",
        {
            **_transition_envelope({"type": "reset"}),
            "input": {
                **_transition_envelope({"type": "reset"})["input"],
                "widget": progressed_widget,
            },
        },
    )

    assert result.artifact["accepted"] is True
    assert result.artifact["canonicalWidget"]["state"]["fen"] == _CHESS_WIDGET["state"]["initialFen"]
