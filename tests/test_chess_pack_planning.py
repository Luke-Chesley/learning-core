from __future__ import annotations

import json

import pytest

from learning_core.contracts.activity import ActivityArtifact, ActivityGenerationInput
from learning_core.contracts.operation import AppContext, PresentationContext, UserAuthoredContext
from learning_core.runtime.context import RuntimeContext
from learning_core.runtime.providers import ModelRuntime
from learning_core.skills.activity_generate.packs.chess.contracts import ChessBuiltExampleSet, ChessExamplePlan
from learning_core.skills.activity_generate.packs.chess.pack import ChessPack
from learning_core.skills.activity_generate.packs.chess.planning import (
    build_chess_example_set,
    render_chess_example_summary,
    validate_chess_artifact_against_example_set,
    validate_chess_example_set,
)


def _payload() -> ActivityGenerationInput:
    return ActivityGenerationInput.model_validate(
        {
            "learner_name": "Alex",
            "subject": "Chess",
            "linked_skill_titles": ["Find the best move"],
            "lesson_draft": {
                "schema_version": "1.0",
                "title": "Escape check",
                "lesson_focus": "Practice move, block, capture responses when in check.",
                "primary_objectives": ["Escape check with a legal response"],
                "success_criteria": ["Choose the right response to check"],
                "total_minutes": 30,
                "blocks": [],
                "materials": [],
                "teacher_notes": [],
                "adaptations": [],
            },
        }
    )


def _context() -> RuntimeContext:
    return RuntimeContext.create(
        operation_name="activity_generate",
        app_context=AppContext(product="test", surface="test"),
        presentation_context=PresentationContext(),
        user_authored_context=UserAuthoredContext(),
    )


class _FakeClient:
    def __init__(self, content: str):
        self.content = content

    def invoke(self, messages):
        return type("Response", (), {"content": self.content})()


def _fake_runtime(content: str) -> ModelRuntime:
    return ModelRuntime(
        provider="test",
        model="test",
        client=_FakeClient(content),
        temperature=0.0,
        max_tokens=1024,
        max_tokens_source="test",
        provider_settings={},
    )


def _plan_json() -> str:
    return json.dumps(
        {
            "lessonFamily": "escape_check_responses",
            "exampleSlots": [
                {
                    "slotId": "escape-move",
                    "taskKind": "escape_check",
                    "conceptTarget": "move",
                    "roleInActivity": "model",
                    "difficulty": "intro",
                    "requiresExplanation": True,
                    "acceptanceMode": "engine_derived_escape_set",
                },
                {
                    "slotId": "escape-block",
                    "taskKind": "escape_check",
                    "conceptTarget": "block",
                    "roleInActivity": "guided_practice",
                    "difficulty": "core",
                    "requiresExplanation": True,
                    "acceptanceMode": "engine_derived_escape_set",
                },
                {
                    "slotId": "escape-capture",
                    "taskKind": "escape_check",
                    "conceptTarget": "capture",
                    "roleInActivity": "check_for_understanding",
                    "difficulty": "core",
                    "requiresExplanation": False,
                    "acceptanceMode": "engine_derived_escape_set",
                },
            ],
        }
    )


def _artifact_from_examples(example_set: ChessBuiltExampleSet) -> ActivityArtifact:
    return ActivityArtifact.model_validate(
        {
            "schemaVersion": "2",
            "title": "Escape check practice",
            "purpose": "Choose the right response to check.",
            "activityKind": "guided_practice",
            "linkedObjectiveIds": [],
            "linkedSkillLabels": ["Find the best move"],
            "estimatedMinutes": 12,
            "interactionMode": "digital",
            "components": [
                {
                    "type": "interactive_widget",
                    "id": example.componentId,
                    "prompt": "White to move.",
                    "required": True,
                    "widget": example.widget,
                }
                for example in example_set.examples
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


def test_chess_pack_needs_planning_for_board_centered_lesson():
    pack = ChessPack()
    assert pack.needs_planning(_payload(), _context()) is True


def test_chess_pack_does_not_plan_for_non_chess_request():
    pack = ChessPack()
    payload = ActivityGenerationInput.model_validate(
        {
            "learner_name": "Alex",
            "subject": "History",
            "linked_skill_titles": ["Ancient Egypt"],
            "lesson_draft": {
                "schema_version": "1.0",
                "title": "Daily life",
                "lesson_focus": "Describe daily life features.",
                "primary_objectives": ["Describe"],
                "success_criteria": ["Name one feature"],
                "total_minutes": 20,
                "blocks": [],
                "materials": [],
                "teacher_notes": [],
                "adaptations": [],
            },
        }
    )
    assert pack.needs_planning(payload, _context()) is False


def test_planning_phase_returns_structured_plan_and_validated_examples():
    pack = ChessPack()
    result = pack.run_planning_phase(_payload(), _context(), _fake_runtime(_plan_json()))

    assert result is not None
    assert result.structured_data["phase"] == "chess_example_planning"
    plan = ChessExamplePlan.model_validate(result.structured_data["plan"])
    assert plan.lessonFamily == "escape_check_responses"
    assert [slot.conceptTarget for slot in plan.exampleSlots[:3]] == ["move", "block", "capture"]
    assert all(slot.acceptanceMode == "engine_derived_escape_set" for slot in plan.exampleSlots)

    example_set = ChessBuiltExampleSet.model_validate(result.structured_data["validated_examples"])
    assert len(example_set.examples) == 3
    assert {example.conceptTarget for example in example_set.examples} == {"move", "block", "capture"}
    assert "validated chess examples" in render_chess_example_summary(example_set).lower()


def test_example_builder_derives_distinct_engine_backed_moves():
    plan = ChessExamplePlan.model_validate(json.loads(_plan_json()))
    example_set = build_chess_example_set(plan)

    assert len({example.fen for example in example_set.examples}) == 3
    assert len({example.componentId for example in example_set.examples}) == 3
    move_example = next(example for example in example_set.examples if example.conceptTarget == "move")
    block_example = next(example for example in example_set.examples if example.conceptTarget == "block")
    capture_example = next(example for example in example_set.examples if example.conceptTarget == "capture")

    assert all(move.moveCategory == "move" for move in move_example.acceptedMoves)
    assert all(move.moveCategory == "block" for move in block_example.acceptedMoves)
    assert all(move.moveCategory == "capture" for move in capture_example.acceptedMoves)

    report = validate_chess_example_set(example_set)
    assert report.valid is True
    assert set(report.coverageTargets) == {"move", "block", "capture"}


def test_duplicate_fen_examples_are_rejected_before_final_composition():
    plan = ChessExamplePlan.model_validate(
        {
            "lessonFamily": "escape_check",
            "exampleSlots": [
                {
                    "slotId": "move-1",
                    "taskKind": "escape_check",
                    "conceptTarget": "move",
                    "roleInActivity": "model",
                    "difficulty": "intro",
                    "requiresExplanation": True,
                },
                {
                    "slotId": "move-2",
                    "taskKind": "escape_check",
                    "conceptTarget": "move",
                    "roleInActivity": "guided_practice",
                    "difficulty": "core",
                    "requiresExplanation": True,
                },
            ],
        }
    )

    with pytest.raises(ValueError):
        build_chess_example_set(plan)


def test_final_activity_validation_detects_drift():
    plan = ChessExamplePlan.model_validate(json.loads(_plan_json()))
    example_set = build_chess_example_set(plan)
    artifact = _artifact_from_examples(example_set)

    report = validate_chess_artifact_against_example_set(artifact, example_set)
    assert report.valid is True

    drifted = artifact.model_copy(deep=True)
    drifted.components[0].widget.evaluation.expectedMoves = ["e4"]
    drift_report = validate_chess_artifact_against_example_set(drifted, example_set)
    assert drift_report.valid is False
    assert drift_report.hardErrors


def test_planning_tools_are_exposed_separately_from_runtime_tools():
    pack = ChessPack()
    planning_tool_names = [tool.name for tool in pack.planning_tools()]
    assert planning_tool_names == [
        "chess_build_example_set",
        "chess_validate_example_set",
        "chess_validate_final_activity",
    ]


def test_planning_phase_uses_recap_slot_for_longer_lessons_when_model_needs_fallback():
    pack = ChessPack()
    payload = _payload()
    runtime = _fake_runtime("not valid json")

    result = pack.run_planning_phase(payload, _context(), runtime)

    assert result is not None
    plan = ChessExamplePlan.model_validate(result.structured_data["plan"])
    assert len(plan.exampleSlots) == 4
    assert plan.exampleSlots[-1].roleInActivity == "recap"
