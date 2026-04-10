from __future__ import annotations

import learning_core.runtime.engine as engine_module

from learning_core.runtime.engine import AgentEngine
from learning_core.runtime.providers import ModelRuntime
from learning_core.skills.catalog import build_skill_registry


_ACTIVITY_SPEC = {
    "schemaVersion": "2",
    "title": "Targeted practice",
    "purpose": "Practice one focused skill.",
    "activityKind": "guided_practice",
    "linkedObjectiveIds": [],
    "linkedSkillTitles": ["targeted practice"],
    "estimatedMinutes": 10,
    "interactionMode": "digital",
    "components": [
        {
            "type": "single_select",
            "id": "pick-one",
            "prompt": "Choose the correct answer.",
            "choices": [
                {"id": "a", "text": "A"},
                {"id": "b", "text": "B", "correct": True, "explanation": "B is the correct option."},
            ],
            "required": True,
        },
        {
            "type": "short_answer",
            "id": "numeric-answer",
            "prompt": "What is one half as a decimal?",
            "expectedAnswer": "0.5",
            "required": True,
        },
        {
            "type": "text_response",
            "id": "explain-plan",
            "prompt": "Explain why your plan works.",
            "required": True,
        },
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
        },
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


class _FakeStructuredInvoker:
    def __init__(self, artifact: dict) -> None:
        self.artifact = artifact

    def invoke(self, _messages):
        return self.artifact


class _FakeClient:
    def __init__(self, artifact: dict) -> None:
        self.artifact = artifact

    def with_structured_output(self, _output_model, **_kwargs):
        return _FakeStructuredInvoker(self.artifact)


def _feedback_envelope(component_id: str, component_type: str, learner_response, expected_answer=None):
    return {
        "input": {
            "activityId": "activity-1",
            "activitySpec": _ACTIVITY_SPEC,
            "componentId": component_id,
            "componentType": component_type,
            "learnerResponse": learner_response,
            "expectedAnswer": expected_answer,
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


def test_activity_feedback_single_select_uses_deterministic_path():
    engine = AgentEngine(build_skill_registry())
    result = engine.execute(
        "activity_feedback",
        _feedback_envelope("pick-one", "single_select", "b"),
    )

    assert result.artifact["status"] == "correct"
    assert result.artifact["evaluationMethod"] == "deterministic"
    assert result.lineage.provider == "deterministic"


def test_activity_feedback_short_answer_supports_numeric_equivalence():
    engine = AgentEngine(build_skill_registry())
    result = engine.execute(
        "activity_feedback",
        _feedback_envelope("numeric-answer", "short_answer", "1/2"),
    )

    assert result.artifact["status"] == "correct"
    assert result.artifact["evaluationMethod"] == "deterministic"


def test_activity_feedback_interactive_widget_chess_supports_expected_move_matching():
    engine = AgentEngine(build_skill_registry())
    result = engine.execute(
        "activity_feedback",
        _feedback_envelope(
            "best-move",
            "interactive_widget",
            {"from": "e2", "to": "b5", "uci": "e2b5", "san": "Qb5+"},
        ),
    )

    assert result.artifact["status"] == "correct"
    assert result.artifact["evaluationMethod"] == "deterministic"
    assert result.artifact["widgetEngineKind"] == "chess"


def test_activity_feedback_falls_back_to_llm_for_soft_judgment(monkeypatch, tmp_path):
    monkeypatch.setenv("LEARNING_CORE_LOG_DIR", str(tmp_path / "logs"))
    monkeypatch.setattr(
        engine_module,
        "build_model_runtime",
        lambda **_kwargs: ModelRuntime(
            provider="test",
            model="fake-activity-feedback",
            client=_FakeClient(
                {
                    "schemaVersion": "1",
                    "componentId": "explain-plan",
                    "componentType": "text_response",
                    "status": "partial",
                    "feedbackMessage": "Your explanation points in the right direction but needs a clearer reason.",
                    "hint": "Name the idea that makes the plan work.",
                    "nextStep": "Add one sentence explaining why the plan is effective.",
                    "confidence": 0.7,
                    "allowRetry": True,
                    "evaluationMethod": "llm",
                    "scoring": {"score": 0.6, "matchedTargets": 1, "totalTargets": 2},
                }
            ),
            temperature=0.0,
            max_tokens=1200,
            max_tokens_source="test",
            provider_settings={},
        ),
    )

    engine = AgentEngine(build_skill_registry())
    result = engine.execute(
        "activity_feedback",
        _feedback_envelope("explain-plan", "text_response", "It works because it is a good idea."),
    )

    assert result.artifact["status"] == "partial"
    assert result.artifact["evaluationMethod"] == "llm"
    assert result.trace.agent_trace["evaluation_method"] == "llm"
