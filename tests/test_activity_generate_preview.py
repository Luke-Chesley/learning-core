import json
from pathlib import Path
from unittest.mock import patch

import pytest

from learning_core.agent import AgentResult, ToolCallEvent
from learning_core.contracts.activity import ActivityArtifact, ActivityGenerationInput
from learning_core.contracts.operation import AppContext, PresentationContext, UserAuthoredContext
from learning_core.runtime.context import RuntimeContext
from learning_core.runtime.engine import AgentEngine
from learning_core.runtime.providers import ModelRuntime
from learning_core.skills.activity_generate.scripts.main import ActivityGenerateSkill, _select_packs
from learning_core.skills.catalog import build_skill_registry

# -- Shared test fixtures --

_LESSON_DRAFT = {
    "schema_version": "1.0",
    "title": "Long Division",
    "lesson_focus": "Learn the long division algorithm.",
    "primary_objectives": ["Divide with support"],
    "success_criteria": ["Finish three problems"],
    "total_minutes": 35,
    "blocks": [
        {
            "type": "model",
            "title": "Model it",
            "minutes": 10,
            "purpose": "Show the method",
            "teacher_action": "Demonstrate on whiteboard",
            "learner_action": "Take notes",
            "materials_needed": [],
            "optional": False,
        }
    ],
    "materials": ["Workbook"],
    "teacher_notes": ["Use D-M-S-B language"],
    "adaptations": [],
    "assessment_artifact": "Workbook page",
}

_VALID_ARTIFACT = {
    "schemaVersion": "2",
    "title": "Place Value Practice",
    "purpose": "Practice identifying digit place values in 5-digit numbers.",
    "activityKind": "guided_practice",
    "linkedObjectiveIds": [],
    "linkedSkillTitles": ["place value"],
    "estimatedMinutes": 15,
    "interactionMode": "digital",
    "components": [
        {
            "type": "paragraph",
            "id": "intro",
            "text": "Work through the following steps.",
        },
        {
            "type": "short_answer",
            "id": "q1",
            "prompt": "What is the value of the digit 4 in 34,827?",
            "hint": "Think about which place the 4 occupies.",
            "required": True,
        },
        {
            "type": "confidence_check",
            "id": "confidence",
            "prompt": "How confident are you?",
            "labels": ["Not yet", "A little", "Getting there", "Pretty good", "Got it!"],
        },
    ],
    "completionRules": {"strategy": "all_interactive_components"},
    "evidenceSchema": {
        "captureKinds": ["answer_response", "confidence_signal"],
        "requiresReview": False,
        "autoScorable": False,
    },
    "scoringModel": {
        "mode": "completion_based",
        "masteryThreshold": 0.8,
        "reviewThreshold": 0.6,
    },
}

_VALID_ARTIFACT_WITH_NULLS = {
    "schemaVersion": "2",
    "title": "Place Value Practice",
    "purpose": "Practice identifying digit place values in 5-digit numbers.",
    "activityKind": "guided_practice",
    "linkedObjectiveIds": [],
    "linkedSkillTitles": ["place value"],
    "estimatedMinutes": 15,
    "interactionMode": "digital",
    "components": [
        {
            "type": "paragraph",
            "id": "intro",
            "text": "Work through the following steps.",
            "markdown": None,
        },
        {
            "type": "short_answer",
            "id": "q1",
            "prompt": "What is the value of the digit 4 in 34,827?",
            "hint": "Think about which place the 4 occupies.",
            "required": True,
        },
        {
            "type": "build_steps",
            "id": "steps",
            "steps": [
                {
                    "id": "step-1",
                    "instruction": "Read the number.",
                    "expectedValue": None,
                }
            ],
        },
    ],
    "completionRules": {
        "strategy": "all_interactive_components",
        "minimumComponents": None,
    },
    "evidenceSchema": {
        "captureKinds": ["answer_response"],
        "requiresReview": False,
        "autoScorable": False,
    },
    "scoringModel": {
        "mode": "completion_based",
        "masteryThreshold": 0.8,
        "reviewThreshold": 0.6,
        "rubricMasteryLevel": None,
        "confidenceMasteryLevel": None,
    },
}

_VALID_CHESS_ARTIFACT = {
    "schemaVersion": "2",
    "title": "Find the tactical move",
    "purpose": "Choose the best move from the board position.",
    "activityKind": "guided_practice",
    "linkedObjectiveIds": [],
    "linkedSkillTitles": ["best move"],
    "estimatedMinutes": 10,
    "interactionMode": "digital",
    "components": [
        {
            "type": "interactive_widget",
            "id": "best-move",
            "prompt": "White to move. Find the queen move that gives check.",
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

_ENVELOPE_DATA = {
    "input": {
        "learner_name": "Alex",
        "workflow_mode": "family_guided",
        "subject": "Math",
        "linked_skill_titles": ["Long Division"],
        "lesson_draft": _LESSON_DRAFT,
    },
    "app_context": {
        "product": "homeschool-v2",
        "surface": "today_workspace",
    },
}


def _make_payload(**overrides):
    data = dict(_ENVELOPE_DATA["input"])
    data.update(overrides)
    return ActivityGenerationInput.model_validate(data)


def _make_context():
    return RuntimeContext.create(
        operation_name="activity_generate",
        app_context=AppContext(product="homeschool-v2", surface="today_workspace"),
        presentation_context=PresentationContext(),
        user_authored_context=UserAuthoredContext(),
    )


def _fake_model_runtime():
    return ModelRuntime(
        provider="openai",
        model="fake-activity-generate",
        client=_FakeClient(),
        temperature=0.2,
        max_tokens=4096,
        max_tokens_source="test",
        provider_settings={},
    )


class _FakeClient:
    """Minimal fake that satisfies model_runtime.client interface for repair calls."""

    def __init__(self, repair_content: str = "{}"):
        self._repair_content = repair_content

    def invoke(self, messages):
        return type("FakeResponse", (), {"content": self._repair_content})()


def _fake_agent_result(artifact_dict: dict, tool_calls: list[ToolCallEvent] | None = None) -> AgentResult:
    return AgentResult(
        final_text=json.dumps(artifact_dict),
        tool_calls=tool_calls or [],
        messages=[],
    )


# -- Preview tests --


def test_activity_generate_preview_includes_lesson_title():
    preview = ActivityGenerateSkill().build_prompt_preview(_make_payload(), _make_context())
    assert "Long Division" in preview.user_prompt
    assert "ActivitySpec" in preview.system_prompt


def test_activity_generate_preview_includes_registry_index():
    preview = ActivityGenerateSkill().build_prompt_preview(_make_payload(), _make_context())
    assert "UI Registry" in preview.user_prompt
    assert "read_ui_spec" in preview.user_prompt
    assert "ui_components/short_answer.md" in preview.user_prompt


def test_activity_generate_preview_uses_pack_aware_tool_guidance():
    preview = ActivityGenerateSkill().build_prompt_preview(_make_payload(), _make_context())
    assert "read_ui_spec" in preview.user_prompt
    assert "Many requests need no doc reads" in preview.user_prompt
    assert "typically 0-2" not in preview.user_prompt
    assert "Math Pack" in preview.user_prompt
    assert "interactive_widget" in preview.user_prompt


def test_registry_index_rows_include_explicit_paths():
    registry_text = Path("learning_core/skills/activity_generate/ui_registry_index.md").read_text(encoding="utf-8")
    assert "| type | use when | avoid when | cost | path |" in registry_text
    assert "ui_components/build_steps.md" in registry_text
    assert "ui_components/interactive_widget.md" in registry_text
    assert "ui_widgets/board_surface__chess.md" in registry_text


def test_pack_selection_detects_math():
    selection = _select_packs(_make_payload())
    assert selection.included_packs == ("math",)
    assert selection.pack_selection_reason["math"]


def test_pack_selection_detects_chess():
    selection = _select_packs(
        _make_payload(
            subject="Chess",
            linked_skill_titles=["Find the best move"],
            lesson_draft={
                **_LESSON_DRAFT,
                "title": "Find the best move",
                "lesson_focus": "Practice candidate moves from one chess position.",
            },
        )
    )
    assert selection.included_packs == ("chess",)
    assert selection.pack_selection_reason["chess"]


def test_pack_selection_can_return_no_pack():
    selection = _select_packs(
        _make_payload(
            subject="History",
            linked_skill_titles=["Ancient Egypt"],
            lesson_draft={
                **_LESSON_DRAFT,
                "title": "Daily life in Ancient Egypt",
                "lesson_focus": "Describe one feature of daily life.",
            },
        )
    )
    assert selection.included_packs == ()


# -- Artifact validation tests --


def test_activity_artifact_accepts_canonical_minimal_spec():
    artifact = ActivityArtifact.model_validate(_VALID_ARTIFACT)
    assert artifact.schemaVersion == "2"
    assert artifact.components[1].type == "short_answer"


def test_activity_artifact_accepts_interactive_widget_component():
    artifact = ActivityArtifact.model_validate(_VALID_CHESS_ARTIFACT)
    assert artifact.components[0].type == "interactive_widget"
    assert artifact.components[0].widget.engineKind == "chess"


def test_activity_artifact_rejects_top_level_chess_board_component():
    invalid = {
        **_VALID_CHESS_ARTIFACT,
        "components": [
            {
                "type": "chess_board",
                "id": "legacy-chess",
                "prompt": "Legacy board",
                "fen": "4k3/8/8/8/8/8/4Q3/4K3 w - - 0 1",
                "orientation": "white",
                "allowMoveInput": True,
                "expectedMoves": ["Qb5+"],
                "required": True,
            }
        ],
    }

    with pytest.raises(Exception):
        ActivityArtifact.model_validate(invalid)


def test_activity_artifact_json_schema_has_no_open_objects():
    schema = ActivityArtifact.model_json_schema()
    open_paths: list[str] = []
    tuple_paths: list[str] = []
    format_paths: list[str] = []

    def walk(node, path: str) -> None:
        if isinstance(node, dict):
            is_object = node.get("type") == "object" or "properties" in node
            if is_object and node.get("additionalProperties") is not False:
                open_paths.append(path)
            if "prefixItems" in node:
                tuple_paths.append(path)
            if "format" in node:
                format_paths.append(path)
            for key, value in node.items():
                walk(value, f"{path}.{key}")
        elif isinstance(node, list):
            for index, value in enumerate(node):
                walk(value, f"{path}[{index}]")

    walk(schema, "$")
    assert open_paths == []
    assert tuple_paths == []
    assert format_paths == []


# -- Execution tests (agent path) --


@patch("learning_core.skills.activity_generate.scripts.main.run_agent_loop")
@patch("learning_core.skills.activity_generate.scripts.main.build_model_runtime")
def test_activity_execute_happy_path(mock_build_runtime, mock_agent_loop, tmp_path):
    import os
    os.environ["LEARNING_CORE_LOG_DIR"] = str(tmp_path / "logs")
    mock_build_runtime.return_value = _fake_model_runtime()
    mock_agent_loop.return_value = _fake_agent_result(_VALID_ARTIFACT)

    engine = AgentEngine(build_skill_registry())
    result = engine.execute("activity_generate", _ENVELOPE_DATA)

    assert result.operation_name == "activity_generate"
    assert result.artifact["schemaVersion"] == "2"
    assert result.artifact["title"] == "Place Value Practice"
    assert result.trace.agent_trace is not None
    assert result.trace.agent_trace["repair_attempted"] is False
    os.environ.pop("LEARNING_CORE_LOG_DIR", None)


@patch("learning_core.skills.activity_generate.scripts.main.run_agent_loop")
@patch("learning_core.skills.activity_generate.scripts.main.build_model_runtime")
def test_activity_execute_with_tool_calls(mock_build_runtime, mock_agent_loop, tmp_path):
    import os
    os.environ["LEARNING_CORE_LOG_DIR"] = str(tmp_path / "logs")
    mock_build_runtime.return_value = _fake_model_runtime()
    mock_agent_loop.return_value = _fake_agent_result(
        _VALID_ARTIFACT,
        tool_calls=[
            ToolCallEvent(
                tool_name="read_ui_spec",
                tool_args={"path": "ui_components/short_answer.md"},
                tool_output="# short_answer\n...",
            ),
        ],
    )

    engine = AgentEngine(build_skill_registry())
    result = engine.execute("activity_generate", _ENVELOPE_DATA)

    assert result.artifact["schemaVersion"] == "2"
    assert result.trace.agent_trace["ui_specs_read"] == ["ui_components/short_answer.md"]
    assert result.trace.agent_trace["included_packs"] == ["math"]
    assert len(result.trace.agent_trace["tool_calls"]) == 1
    assert result.trace.agent_trace["tool_calls"][0]["output_preview"] == "# short_answer\n..."
    assert result.trace.agent_trace["tool_calls"][0]["output_hash"]
    os.environ.pop("LEARNING_CORE_LOG_DIR", None)


@patch("learning_core.skills.activity_generate.scripts.main.run_agent_loop")
@patch("learning_core.skills.activity_generate.scripts.main.build_model_runtime")
def test_activity_execute_omits_null_optional_fields(mock_build_runtime, mock_agent_loop, tmp_path):
    import os
    os.environ["LEARNING_CORE_LOG_DIR"] = str(tmp_path / "logs")
    mock_build_runtime.return_value = _fake_model_runtime()
    mock_agent_loop.return_value = _fake_agent_result(_VALID_ARTIFACT_WITH_NULLS)

    engine = AgentEngine(build_skill_registry())
    result = engine.execute("activity_generate", _ENVELOPE_DATA)

    paragraph = result.artifact["components"][0]
    build_steps = result.artifact["components"][2]
    assert "markdown" not in paragraph
    assert "expectedValue" not in build_steps["steps"][0]
    assert "minimumComponents" not in result.artifact["completionRules"]
    assert "rubricMasteryLevel" not in result.artifact["scoringModel"]
    assert "confidenceMasteryLevel" not in result.artifact["scoringModel"]
    os.environ.pop("LEARNING_CORE_LOG_DIR", None)


@patch("learning_core.skills.activity_generate.scripts.main.run_agent_loop")
@patch("learning_core.skills.activity_generate.scripts.main.build_model_runtime")
def test_activity_execute_repair_on_invalid_json(mock_build_runtime, mock_agent_loop, tmp_path):
    import os
    os.environ["LEARNING_CORE_LOG_DIR"] = str(tmp_path / "logs")

    # Return a client whose invoke() returns the valid artifact (for repair pass).
    fake_runtime = ModelRuntime(
        provider="openai",
        model="fake-activity-generate",
        client=_FakeClient(repair_content=json.dumps(_VALID_ARTIFACT)),
        temperature=0.2,
        max_tokens=4096,
        max_tokens_source="test",
        provider_settings={},
    )
    mock_build_runtime.return_value = fake_runtime

    # Agent returns invalid JSON that fails validation.
    mock_agent_loop.return_value = AgentResult(
        final_text='{"schemaVersion": "2", "title": "Bad"}',
        tool_calls=[],
        messages=[],
    )

    engine = AgentEngine(build_skill_registry())
    result = engine.execute("activity_generate", _ENVELOPE_DATA)

    assert result.artifact["schemaVersion"] == "2"
    assert result.trace.agent_trace["repair_attempted"] is True
    assert result.trace.agent_trace["repair_succeeded"] is True
    os.environ.pop("LEARNING_CORE_LOG_DIR", None)


@patch("learning_core.skills.activity_generate.scripts.main.run_agent_loop")
@patch("learning_core.skills.activity_generate.scripts.main.build_model_runtime")
def test_activity_execute_repair_failure_raises(mock_build_runtime, mock_agent_loop, tmp_path):
    import os
    import pytest
    from learning_core.runtime.errors import ContractValidationError

    os.environ["LEARNING_CORE_LOG_DIR"] = str(tmp_path / "logs")

    # Repair returns still-invalid JSON.
    fake_runtime = ModelRuntime(
        provider="openai",
        model="fake-activity-generate",
        client=_FakeClient(repair_content='{"still": "broken"}'),
        temperature=0.2,
        max_tokens=4096,
        max_tokens_source="test",
        provider_settings={},
    )
    mock_build_runtime.return_value = fake_runtime

    mock_agent_loop.return_value = AgentResult(
        final_text='{"schemaVersion": "2", "title": "Bad"}',
        tool_calls=[],
        messages=[],
    )

    engine = AgentEngine(build_skill_registry())
    with pytest.raises(ContractValidationError, match="repair"):
        engine.execute("activity_generate", _ENVELOPE_DATA)
    os.environ.pop("LEARNING_CORE_LOG_DIR", None)


@patch("learning_core.skills.activity_generate.scripts.main.run_agent_loop")
@patch("learning_core.skills.activity_generate.scripts.main.build_model_runtime")
def test_activity_execute_extracts_json_from_markdown_fence(mock_build_runtime, mock_agent_loop, tmp_path):
    import os
    os.environ["LEARNING_CORE_LOG_DIR"] = str(tmp_path / "logs")
    mock_build_runtime.return_value = _fake_model_runtime()

    fenced = f"Here is the activity:\n```json\n{json.dumps(_VALID_ARTIFACT)}\n```"
    mock_agent_loop.return_value = AgentResult(
        final_text=fenced,
        tool_calls=[],
        messages=[],
    )

    engine = AgentEngine(build_skill_registry())
    result = engine.execute("activity_generate", _ENVELOPE_DATA)
    assert result.artifact["schemaVersion"] == "2"
    os.environ.pop("LEARNING_CORE_LOG_DIR", None)
