"""Tests that packs own their tools and that tool exposure is driven by pack selection."""
import json
from unittest.mock import patch

from learning_core.agent import AgentResult, ToolCallEvent
from learning_core.contracts.activity import ActivityGenerationInput
from learning_core.contracts.operation import AppContext, PresentationContext, UserAuthoredContext
from learning_core.runtime.context import RuntimeContext
from learning_core.runtime.engine import AgentEngine
from learning_core.runtime.providers import ModelRuntime
from learning_core.skills.activity_generate.packs import ALL_PACKS
from learning_core.skills.activity_generate.packs.base import Pack
from learning_core.skills.activity_generate.packs.chess.pack import ChessPack
from learning_core.skills.activity_generate.packs.chess.tools import CHESS_TOOLS
from learning_core.skills.activity_generate.packs.math.pack import MathPack
from learning_core.skills.activity_generate.scripts.main import ActivityGenerateSkill, _select_packs
from learning_core.skills.activity_generate.scripts.tooling import read_ui_spec
from learning_core.skills.catalog import build_skill_registry


_LESSON_DRAFT = {
    "schema_version": "1.0",
    "title": "Placeholder",
    "lesson_focus": "Placeholder focus",
    "primary_objectives": ["Learn"],
    "success_criteria": ["Done"],
    "total_minutes": 30,
    "blocks": [],
    "materials": [],
    "teacher_notes": [],
    "adaptations": [],
}

_VALID_ARTIFACT = {
    "schemaVersion": "2",
    "title": "Test",
    "purpose": "Testing pack isolation.",
    "activityKind": "guided_practice",
    "linkedObjectiveIds": [],
    "linkedSkillLabels": [],
    "estimatedMinutes": 10,
    "interactionMode": "digital",
    "components": [
        {"type": "paragraph", "id": "p1", "text": "Hello."},
        {
            "type": "short_answer",
            "id": "q1",
            "prompt": "Answer?",
            "required": True,
        },
    ],
    "completionRules": {"strategy": "all_interactive_components"},
    "evidenceSchema": {
        "captureKinds": ["answer_response"],
        "requiresReview": False,
        "autoScorable": False,
    },
    "scoringModel": {
        "mode": "completion_based",
        "masteryThreshold": 0.8,
        "reviewThreshold": 0.6,
    },
}


def _make_payload(**overrides):
    data = {
        "learner_name": "Test",
        "subject": "General",
        "linked_skill_titles": [],
        "lesson_draft": _LESSON_DRAFT,
    }
    data.update(overrides)
    return ActivityGenerationInput.model_validate(data)


def _make_context():
    return RuntimeContext.create(
        operation_name="activity_generate",
        app_context=AppContext(product="test", surface="test"),
        presentation_context=PresentationContext(),
        user_authored_context=UserAuthoredContext(),
    )


def _fake_runtime():
    class _Stub:
        def invoke(self, messages):
            return type("R", (), {"content": "{}"})()
    return ModelRuntime(
        provider="openai", model="fake", client=_Stub(),
        temperature=0.2, max_tokens=4096, max_tokens_source="test",
        provider_settings={},
    )


# -- Pack protocol --


def test_all_packs_satisfy_protocol():
    for pack in ALL_PACKS:
        assert isinstance(pack, Pack)
        assert isinstance(pack.name, str)
        assert isinstance(pack.keywords, tuple)
        assert isinstance(pack.prompt_sections(), list)
        assert isinstance(pack.needs_planning(_make_payload(), _make_context()), bool)
        assert isinstance(pack.tools(), list)


def test_chess_pack_exposes_tools():
    pack = ChessPack()
    tool_names = [t.name for t in pack.tools()]
    assert set(tool_names) == {
        "chess_legal_moves",
        "chess_describe_position",
        "chess_apply_move",
        "chess_normalize_move",
        "chess_build_example_set",
        "chess_validate_example_set",
        "chess_validate_final_activity",
        "chess_validate_widget_config",
    }


def test_math_pack_exposes_tools():
    pack = MathPack()
    tool_names = [t.name for t in pack.tools()]
    assert set(tool_names) == {
        "math_validate_widget_config",
    }


def test_chess_pack_prompt_sections_are_nonempty():
    sections = ChessPack().prompt_sections()
    assert len(sections) == 3
    assert all(len(s) > 0 for s in sections)


def test_math_pack_prompt_sections_are_nonempty():
    sections = MathPack().prompt_sections()
    assert len(sections) == 3
    assert all(len(s) > 0 for s in sections)


# -- Tool activation via pack selection --


@patch("learning_core.skills.activity_generate.scripts.main.run_agent_loop")
@patch("learning_core.skills.activity_generate.scripts.main.build_model_runtime")
def test_chess_request_gets_chess_tools(mock_build_runtime, mock_agent_loop, tmp_path):
    import os
    os.environ["LEARNING_CORE_LOG_DIR"] = str(tmp_path / "logs")
    mock_build_runtime.return_value = _fake_runtime()
    mock_agent_loop.return_value = AgentResult(
        final_text=json.dumps(_VALID_ARTIFACT), tool_calls=[], messages=[],
    )

    envelope = {
        "input": {
            "learner_name": "Test",
            "subject": "Chess",
            "linked_skill_titles": ["Find the best move"],
            "lesson_draft": {**_LESSON_DRAFT, "title": "Chess tactics", "lesson_focus": "Find candidate moves."},
        },
        "app_context": {"product": "test", "surface": "test"},
    }
    engine = AgentEngine(build_skill_registry())
    result = engine.execute("activity_generate", envelope)

    active = result.trace.agent_trace["active_tools"]
    assert "read_ui_spec" in active
    assert "chess_legal_moves" in active
    assert "chess_apply_move" in active
    assert "chess_build_example_set" in active
    assert result.trace.agent_trace["included_packs"] == ["chess"]
    os.environ.pop("LEARNING_CORE_LOG_DIR", None)


@patch("learning_core.skills.activity_generate.scripts.main.run_agent_loop")
@patch("learning_core.skills.activity_generate.scripts.main.build_model_runtime")
def test_history_request_gets_base_tools_only(mock_build_runtime, mock_agent_loop, tmp_path):
    import os
    os.environ["LEARNING_CORE_LOG_DIR"] = str(tmp_path / "logs")
    mock_build_runtime.return_value = _fake_runtime()
    mock_agent_loop.return_value = AgentResult(
        final_text=json.dumps(_VALID_ARTIFACT), tool_calls=[], messages=[],
    )

    envelope = {
        "input": {
            "learner_name": "Test",
            "subject": "History",
            "linked_skill_titles": ["Ancient Egypt"],
            "lesson_draft": {
                **_LESSON_DRAFT,
                "title": "Daily life in Ancient Egypt",
                "lesson_focus": "Describe daily life features.",
            },
        },
        "app_context": {"product": "test", "surface": "test"},
    }
    engine = AgentEngine(build_skill_registry())
    result = engine.execute("activity_generate", envelope)

    active = result.trace.agent_trace["active_tools"]
    assert active == ["read_ui_spec"]
    assert result.trace.agent_trace["included_packs"] == []
    os.environ.pop("LEARNING_CORE_LOG_DIR", None)


@patch("learning_core.skills.activity_generate.scripts.main.run_agent_loop")
@patch("learning_core.skills.activity_generate.scripts.main.build_model_runtime")
def test_math_request_gets_math_tools(mock_build_runtime, mock_agent_loop, tmp_path):
    """Math pack is active and contributes its validation tool."""
    import os
    os.environ["LEARNING_CORE_LOG_DIR"] = str(tmp_path / "logs")
    mock_build_runtime.return_value = _fake_runtime()
    mock_agent_loop.return_value = AgentResult(
        final_text=json.dumps(_VALID_ARTIFACT), tool_calls=[], messages=[],
    )

    envelope = {
        "input": {
            "learner_name": "Test",
            "subject": "Math",
            "linked_skill_titles": ["Long Division"],
            "lesson_draft": {**_LESSON_DRAFT, "title": "Long Division", "lesson_focus": "Learn division."},
        },
        "app_context": {"product": "test", "surface": "test"},
    }
    engine = AgentEngine(build_skill_registry())
    result = engine.execute("activity_generate", envelope)

    active = result.trace.agent_trace["active_tools"]
    assert "read_ui_spec" in active
    assert "math_validate_widget_config" in active
    assert result.trace.agent_trace["included_packs"] == ["math"]
    os.environ.pop("LEARNING_CORE_LOG_DIR", None)


# -- Chess tools work from new location --


def test_chess_tools_from_pack_work():
    from learning_core.skills.activity_generate.packs.chess.tools import (
        chess_legal_moves,
        chess_describe_position,
        chess_apply_move,
        chess_normalize_move,
    )
    start_fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"

    result = chess_legal_moves.invoke({"fen": start_fen})
    parsed = json.loads(result)
    san_moves = [m["san"] for m in parsed["legalMoves"]]
    assert "e4" in san_moves

    result = chess_describe_position.invoke({"fen": start_fen})
    parsed = json.loads(result)
    assert parsed["sideToMove"] == "white"

    result = chess_apply_move.invoke({"fen": start_fen, "move": "e4"})
    parsed = json.loads(result)
    assert "fenAfter" in parsed

    result = chess_normalize_move.invoke({"fen": start_fen, "move": "e2e4"})
    parsed = json.loads(result)
    assert parsed["san"] == "e4"


# -- read_ui_spec still works from base tooling --


def test_read_ui_spec_still_works():
    result = read_ui_spec.invoke({"path": "ui_components/short_answer.md"})
    assert "# short_answer" in result
