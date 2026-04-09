from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

import learning_core.runtime.engine as engine_module
from learning_core.contracts.lesson_draft import LESSON_SHAPE_VALUES, StructuredLessonDraft
from learning_core.contracts.operation import AppContext, PresentationContext, UserAuthoredContext
from learning_core.contracts.session_plan import SessionPlanGenerationRequest
from learning_core.runtime.context import RuntimeContext
from learning_core.runtime.engine import AgentEngine
from learning_core.runtime.errors import ContractValidationError
from learning_core.runtime.providers import ModelRuntime
from learning_core.skills.catalog import build_skill_registry
from learning_core.skills.session_generate.scripts.main import SessionGenerateSkill


def _lesson_artifact(lesson_shape: str) -> dict:
    return {
        "schema_version": "1.0",
        "title": "Chess Check Basics",
        "lesson_focus": "Practice answering check and responding to 1. e4.",
        "primary_objectives": [
            "Respond correctly to 1. e4",
            "Recognize check",
        ],
        "success_criteria": [
            "Learner gives one legal reply to 1. e4",
            "Learner names one legal escape from check",
        ],
        "total_minutes": 20,
        "blocks": [
            {
                "type": "demonstration",
                "title": "Show the rule",
                "minutes": 10,
                "purpose": "Introduce the pattern",
                "teacher_action": "Set up one board position and model the response.",
                "learner_action": "Watch, then name the move.",
                "check_for": "Learner names the move and the threat.",
                "materials_needed": ["Chessboard"],
                "optional": False,
            },
            {
                "type": "check_for_understanding",
                "title": "Quick check",
                "minutes": 10,
                "purpose": "Verify the learner can apply the rule",
                "teacher_action": "Show one more position and ask for a legal response.",
                "learner_action": "Choose the move and explain why.",
                "check_for": "Learner picks a legal response.",
                "materials_needed": ["Chessboard"],
                "optional": False,
            },
        ],
        "materials": ["Chessboard"],
        "teacher_notes": ["Keep prompts short."],
        "adaptations": [{"trigger": "if_struggles", "action": "Reduce to one example."}],
        "lesson_shape": lesson_shape,
    }


class _FakeStructuredInvoker:
    def __init__(self, artifact: dict) -> None:
        self.artifact = artifact

    def invoke(self, _messages):
        return self.artifact


class _FakeClient:
    def __init__(self, artifact: dict) -> None:
        self.artifact = artifact
        self.structured_output_method = None

    def with_structured_output(self, _output_model, **kwargs):
        self.structured_output_method = kwargs.get("method")
        return _FakeStructuredInvoker(self.artifact)


def _session_generate_envelope() -> dict:
    return {
        "input": {
            "topic": "Responding correctly to 1. e4",
            "lessonShape": "direct_instruction",
        },
        "app_context": {
            "product": "homeschool-v2",
            "surface": "today",
        },
    }


def test_session_plan_request_rejects_noncanonical_lesson_shape():
    with pytest.raises(ValidationError):
        SessionPlanGenerationRequest.model_validate(
            {
                "topic": "Responding correctly to 1. e4",
                "lessonShape": "Short teach-practice-check sequence",
            }
        )


def test_structured_lesson_draft_rejects_prose_lesson_shape():
    with pytest.raises(ValidationError):
        StructuredLessonDraft.model_validate(
            _lesson_artifact("Short teach-practice-check sequence")
        )


def test_structured_lesson_draft_accepts_canonical_lesson_shape():
    artifact = StructuredLessonDraft.model_validate(
        _lesson_artifact("direct_instruction")
    )

    assert artifact.lesson_shape == "direct_instruction"


def test_session_generate_prompt_preview_constrains_lesson_shape_values():
    payload = SessionPlanGenerationRequest.model_validate(
        {
            "topic": "Responding correctly to 1. e4",
            "lessonShape": "direct_instruction",
        }
    )

    preview = SessionGenerateSkill().build_prompt_preview(
        payload,
        RuntimeContext.create(
            operation_name="session_generate",
            app_context=AppContext(product="homeschool-v2", surface="today"),
            presentation_context=PresentationContext(),
            user_authored_context=UserAuthoredContext(),
        ),
    )

    for lesson_shape in LESSON_SHAPE_VALUES:
        assert lesson_shape in preview.system_prompt
        assert lesson_shape in preview.user_prompt
    assert "machine-readable metadata" in preview.system_prompt
    assert "do not emit descriptive prose labels" in preview.system_prompt.lower()
    assert (
        "Lesson shape preference (canonical lesson_shape slug; reuse exactly if included): "
        "direct_instruction"
    ) in preview.user_prompt


def test_session_generate_execute_rejects_prose_lesson_shape(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("LEARNING_CORE_LOG_DIR", str(tmp_path / "logs"))
    monkeypatch.setattr(
        engine_module,
        "build_model_runtime",
        lambda **_kwargs: ModelRuntime(
            provider="test",
            model="fake-session-generate",
            client=_FakeClient(_lesson_artifact("Short teach-practice-check sequence")),
            temperature=0.2,
            max_tokens=4096,
            max_tokens_source="test",
            provider_settings={},
        ),
    )

    engine = AgentEngine(build_skill_registry())

    with pytest.raises(ContractValidationError):
        engine.execute("session_generate", _session_generate_envelope())


def test_session_generate_execute_accepts_canonical_lesson_shape(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("LEARNING_CORE_LOG_DIR", str(tmp_path / "logs"))
    monkeypatch.setattr(
        engine_module,
        "build_model_runtime",
        lambda **_kwargs: ModelRuntime(
            provider="test",
            model="fake-session-generate",
            client=_FakeClient(_lesson_artifact("direct_instruction")),
            temperature=0.2,
            max_tokens=4096,
            max_tokens_source="test",
            provider_settings={},
        ),
    )

    engine = AgentEngine(build_skill_registry())
    result = engine.execute("session_generate", _session_generate_envelope())

    assert result.artifact["lesson_shape"] == "direct_instruction"


def test_openai_structured_output_uses_function_calling(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("LEARNING_CORE_LOG_DIR", str(tmp_path / "logs"))
    fake_client = _FakeClient(_lesson_artifact("direct_instruction"))
    monkeypatch.setattr(
        engine_module,
        "build_model_runtime",
        lambda **_kwargs: ModelRuntime(
            provider="openai",
            model="fake-session-generate",
            client=fake_client,
            temperature=0.2,
            max_tokens=4096,
            max_tokens_source="test",
            provider_settings={},
        ),
    )

    engine = AgentEngine(build_skill_registry())
    result = engine.execute("session_generate", _session_generate_envelope())

    assert result.artifact["lesson_shape"] == "direct_instruction"
    assert fake_client.structured_output_method == "function_calling"


def test_ollama_structured_output_does_not_use_openai_method(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("LEARNING_CORE_LOG_DIR", str(tmp_path / "logs"))
    fake_client = _FakeClient(_lesson_artifact("direct_instruction"))
    monkeypatch.setattr(
        engine_module,
        "build_model_runtime",
        lambda **_kwargs: ModelRuntime(
            provider="ollama",
            model="fake-session-generate",
            client=fake_client,
            temperature=0.2,
            max_tokens=4096,
            max_tokens_source="test",
            provider_settings={},
        ),
    )

    engine = AgentEngine(build_skill_registry())
    result = engine.execute("session_generate", _session_generate_envelope())

    assert result.artifact["lesson_shape"] == "direct_instruction"
    assert fake_client.structured_output_method is None
