import json
from pathlib import Path
from unittest.mock import patch

import chess

from learning_core.agent import AgentResult
from learning_core.contracts.activity import ActivityArtifact, ActivityGenerationInput
from learning_core.contracts.operation import AppContext, PresentationContext, UserAuthoredContext
from learning_core.runtime.context import RuntimeContext
from learning_core.runtime.engine import AgentEngine
from learning_core.runtime.providers import ModelRuntime
from learning_core.skills.activity_generate.packs.chess.contracts import ChessBuiltExampleSet, ChessExamplePlan
from learning_core.skills.activity_generate.packs.chess.pack import ChessPack
from learning_core.skills.activity_generate.packs.base import PackValidationContext
from learning_core.skills.activity_generate.packs.chess.planning import (
    build_chess_example_set,
    plan_chess_examples,
    validate_chess_example_set,
)
from learning_core.skills.activity_generate.validation.widgets import normalize_and_validate_widget_activity
from learning_core.skills.catalog import build_skill_registry


_LESSON_DRAFT = {
    "schema_version": "1.0",
    "title": "Escape check",
    "lesson_focus": "Use the board to practice how to escape check by move, block, or capture.",
    "primary_objectives": ["Use move, block, and capture to respond to check."],
    "success_criteria": ["Solve one move, one block, and one capture position."],
    "total_minutes": 18,
    "blocks": [],
    "materials": [],
    "teacher_notes": [],
    "adaptations": [],
}


class _FakeClient:
    def __init__(self, content: str = "{}"):
        self._content = content

    def invoke(self, messages):
        return type("FakeResponse", (), {"content": self._content})()


def _fake_runtime(content: str = "{}") -> ModelRuntime:
    return ModelRuntime(
        provider="openai",
        model="fake",
        client=_FakeClient(content),
        temperature=0.2,
        max_tokens=4096,
        max_tokens_source="test",
        provider_settings={},
    )


def _make_payload(**overrides) -> ActivityGenerationInput:
    data = {
        "learner_name": "Alex",
        "subject": "Chess",
        "linked_skill_titles": ["Escape check"],
        "lesson_draft": _LESSON_DRAFT,
    }
    data.update(overrides)
    return ActivityGenerationInput.model_validate(data)


def _make_context() -> RuntimeContext:
    return RuntimeContext.create(
        operation_name="activity_generate",
        app_context=AppContext(product="test", surface="test"),
        presentation_context=PresentationContext(),
        user_authored_context=UserAuthoredContext(),
    )


def _artifact_from_example_set(example_set: ChessBuiltExampleSet) -> dict:
    components = []
    for index, example in enumerate(example_set.examples):
        widget = json.loads(json.dumps(example.widget))
        if index > 0:
            widget["display"]["boardRole"] = "supporting"
        components.append(
            {
                "type": "interactive_widget",
                "id": example.componentId,
                "prompt": f"{example.sideToMove.title()} to move. Escape check by {example.conceptTarget}.",
                "required": True,
                "widget": widget,
            }
        )

    return {
        "schemaVersion": "2",
        "title": "Escape check practice",
        "purpose": "Use validated chess examples for move, block, and capture.",
        "activityKind": "guided_practice",
        "linkedObjectiveIds": [],
        "linkedSkillTitles": ["Escape check"],
        "estimatedMinutes": 12,
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


def test_chess_pack_planning_phase_runs_for_board_centered_lessons():
    pack = ChessPack()
    payload = _make_payload()
    context = _make_context()

    result = pack.run_planning_phase(payload, context, _fake_runtime())

    assert pack.needs_planning(payload, context) is True
    assert result is not None
    assert result.pack_name == "chess"
    assert "validated_examples" in result.structured_data


def test_chess_planning_output_is_structured_plan_not_final_artifact():
    result = ChessPack().run_planning_phase(_make_payload(), _make_context(), _fake_runtime())

    assert result is not None
    plan = result.structured_data["plan"]
    assert "exampleSlots" in plan
    assert "components" not in plan
    assert "schemaVersion" not in plan


def test_chess_example_builder_returns_distinct_examples_with_engine_moves():
    example_set = build_chess_example_set(plan_chess_examples(_make_payload(), _make_context(), _fake_runtime()))

    fens = [example.fen for example in example_set.examples]
    assert len(fens) == len(set(fens))
    for example in example_set.examples:
        board = chess.Board(example.fen)
        checker_squares = set(board.checkers())
        for move in example.acceptedMoves:
            parsed = chess.Move.from_uci(move.uci)
            piece = board.piece_at(parsed.from_square)
            assert piece is not None
            after = board.copy(stack=False)
            after.push(parsed)
            assert after.is_check() is False
            if example.conceptTarget == "move":
                assert piece.piece_type == chess.KING
            if example.conceptTarget == "capture":
                assert parsed.to_square in checker_squares


def test_move_block_capture_lesson_gets_distinct_concept_coverage():
    example_set = build_chess_example_set(plan_chess_examples(_make_payload(), _make_context(), _fake_runtime()))
    concepts = [example.conceptTarget for example in example_set.examples[:3]]

    assert set(concepts) == {"move", "block", "capture"}


def test_duplicate_fens_are_prevented_before_final_composition():
    plan = ChessExamplePlan.model_validate(
        {
            "allowAdditionalBoardExamples": False,
            "exampleSlots": [
                {"slotId": "move-1", "taskKind": "escape_check", "conceptTarget": "move", "roleInActivity": "model"},
                {"slotId": "move-2", "taskKind": "escape_check", "conceptTarget": "move", "roleInActivity": "guided_practice"},
                {
                    "slotId": "move-3",
                    "taskKind": "escape_check",
                    "conceptTarget": "move",
                    "roleInActivity": "check_for_understanding",
                },
            ],
        }
    )

    try:
        build_chess_example_set(plan)
    except ValueError as error:
        assert "No distinct chess catalog example" in str(error)
    else:
        raise AssertionError("Expected duplicate-position prevention to fail before final composition.")


@patch("learning_core.skills.activity_generate.scripts.main.run_agent_loop")
@patch("learning_core.skills.activity_generate.scripts.main.build_model_runtime")
def test_final_activity_generation_composes_from_validated_examples(mock_build_runtime, mock_agent_loop, tmp_path):
    import os

    os.environ["LEARNING_CORE_LOG_DIR"] = str(tmp_path / "logs")
    payload = _make_payload()
    example_set = build_chess_example_set(plan_chess_examples(payload, _make_context(), _fake_runtime()))
    repaired_artifact = _artifact_from_example_set(example_set)
    mock_build_runtime.return_value = _fake_runtime(json.dumps(repaired_artifact))
    mock_agent_loop.return_value = AgentResult(
        final_text=json.dumps(repaired_artifact),
        tool_calls=[],
        messages=[],
    )

    engine = AgentEngine(build_skill_registry())
    result = engine.execute(
        "activity_generate",
        {
            "input": payload.model_dump(mode="json"),
            "app_context": {"product": "test", "surface": "test"},
        },
    )

    trace = result.trace.agent_trace
    assert "pack_planning_results" in trace
    assert trace["pack_validation_results"]["chess"]["planning_applied"] is True
    assert trace["pack_tool_repair_triggered"] is False
    os.environ.pop("LEARNING_CORE_LOG_DIR", None)


def test_final_artifact_does_not_drift_from_validated_example_data():
    payload = _make_payload()
    planning_result = ChessPack().run_planning_phase(payload, _make_context(), _fake_runtime())
    assert planning_result is not None
    example_set = ChessBuiltExampleSet.model_validate(planning_result.structured_data["validated_examples"])
    artifact_dict = _artifact_from_example_set(example_set)
    artifact_dict["components"][0]["widget"]["evaluation"]["expectedMoves"] = ["e1e2"]
    artifact = ActivityArtifact.model_validate(artifact_dict)

    _normalized, hard_errors, _soft_warnings = normalize_and_validate_widget_activity(
        artifact,
        [ChessPack()],
        {"chess": PackValidationContext(planning_result=planning_result)},
    )

    assert any("expectedMoves" in error for error in hard_errors)


def test_pack_local_chess_logic_stays_inside_chess_pack_modules():
    main_source = Path("learning_core/skills/activity_generate/scripts/main.py").read_text(encoding="utf-8")
    assert "escape_check" not in main_source


def test_non_chess_requests_do_not_trigger_chess_planning():
    payload = _make_payload(
        subject="History",
        linked_skill_titles=["Ancient Egypt"],
        lesson_draft={**_LESSON_DRAFT, "title": "Ancient Egypt", "lesson_focus": "Summarize one daily-life fact."},
    )

    assert ChessPack().needs_planning(payload, _make_context()) is False
