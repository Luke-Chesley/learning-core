from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

import learning_core.runtime.engine as engine_module
from learning_core.contracts.lesson_draft import (
    LESSON_BLOCK_TYPE_VALUES,
    LESSON_SHAPE_VALUES,
    StructuredLessonDraft,
)
from learning_core.contracts.operation import AppContext, PresentationContext, UserAuthoredContext
from learning_core.contracts.session_plan import SessionPlanGenerationRequest
from learning_core.runtime.context import RuntimeContext
from learning_core.runtime.engine import AgentEngine
from learning_core.runtime.errors import ContractValidationError
from learning_core.runtime.providers import ModelRuntime
from learning_core.skills.catalog import build_skill_registry
from learning_core.skills.session_generate.scripts.main import SessionGenerateSkill

ALLOWED_CLOUD_URL = (
    "https://upload.wikimedia.org/wikipedia/commons/b/b5/"
    "Cumulus_clouds_in_fair_weather.jpeg"
)


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


class _FakeTextResponse:
    def __init__(self, content: str) -> None:
        self.content = content


class _FakeClient:
    def __init__(self, artifact: dict) -> None:
        self.artifact = artifact
        self.structured_output_method = None

    def with_structured_output(self, _output_model, **kwargs):
        self.structured_output_method = kwargs.get("method")
        return _FakeStructuredInvoker(self.artifact)

    def invoke(self, _messages):
        return _FakeTextResponse(json.dumps(self.artifact))


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


def test_structured_lesson_draft_accepts_allowed_visual_aid_reference():
    artifact = _lesson_artifact("direct_instruction")
    artifact["visual_aids"] = [
        {
            "id": "cloud-photo",
            "title": "Cumulus cloud reference",
            "kind": "reference_image",
            "url": ALLOWED_CLOUD_URL,
            "alt": "White cumulus clouds against a blue sky.",
        }
    ]
    artifact["blocks"][0]["visual_aid_ids"] = ["cloud-photo"]

    parsed = StructuredLessonDraft.model_validate(artifact)

    assert parsed.visual_aids[0].url == ALLOWED_CLOUD_URL
    assert parsed.blocks[0].visual_aid_ids == ["cloud-photo"]


def test_structured_lesson_draft_rejects_disallowed_visual_aid_url():
    artifact = _lesson_artifact("direct_instruction")
    artifact["visual_aids"] = [
        {
            "id": "cloud-photo",
            "title": "Random cloud image",
            "kind": "reference_image",
            "url": "https://example.com/cloud.jpg",
            "alt": "Cloud image.",
        }
    ]

    with pytest.raises(ValidationError):
        StructuredLessonDraft.model_validate(artifact)


def test_structured_lesson_draft_rejects_unknown_visual_aid_reference():
    artifact = _lesson_artifact("direct_instruction")
    artifact["blocks"][0]["visual_aid_ids"] = ["missing-photo"]

    with pytest.raises(ValidationError):
        StructuredLessonDraft.model_validate(artifact)


def test_structured_lesson_draft_rejects_lesson_shape_as_block_type():
    artifact = _lesson_artifact("practice_heavy")
    artifact["blocks"][0]["type"] = "practice_heavy"

    with pytest.raises(ValidationError):
        StructuredLessonDraft.model_validate(artifact)


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
    for block_type in LESSON_BLOCK_TYPE_VALUES:
        assert block_type in preview.system_prompt
        assert block_type in preview.user_prompt
    assert "machine-readable metadata" in preview.system_prompt
    assert "do not emit descriptive prose labels" in preview.system_prompt.lower()
    assert "Never use a lesson_shape slug as blocks[].type" in preview.user_prompt
    assert (
        "Lesson shape preference (canonical lesson_shape slug; reuse exactly if included): "
        "direct_instruction"
    ) in preview.user_prompt


def test_session_generate_prompt_preview_lists_only_allowed_visual_aid_candidates():
    payload = SessionPlanGenerationRequest.model_validate(
        {
            "topic": "Cloud observation",
            "context": {
                "visualAidCandidates": [
                    {
                        "id": "cloud-photo",
                        "title": "Cumulus cloud reference",
                        "url": ALLOWED_CLOUD_URL,
                        "sourceName": "Wikimedia Commons",
                    },
                    {
                        "id": "random-photo",
                        "title": "Random cloud image",
                        "url": "https://example.com/cloud.jpg",
                        "sourceName": "Example",
                    },
                ]
            },
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

    assert "Allowed visual-aid candidates:" in preview.user_prompt
    assert ALLOWED_CLOUD_URL in preview.user_prompt
    assert "https://example.com/cloud.jpg" in preview.user_prompt
    allowed_section = preview.user_prompt.split("Allowed visual-aid candidates:", 1)[1].split("\nObjectives:", 1)[0]
    assert ALLOWED_CLOUD_URL in allowed_section
    assert "https://example.com/cloud.jpg" not in allowed_section


def test_session_generate_prompt_preview_omits_visual_aids_when_no_candidates():
    payload = SessionPlanGenerationRequest.model_validate(
        {
            "topic": "Cloud observation",
            "context": {
                "visualAidCandidates": [
                    {
                        "id": "random-photo",
                        "title": "Random cloud image",
                        "url": "https://example.com/cloud.jpg",
                    },
                ]
            },
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

    assert "Allowed visual-aid candidates: none. Omit visual_aids and visual_aid_ids." in preview.user_prompt


def test_session_generate_validation_retry_corrects_block_type_values():
    payload = SessionPlanGenerationRequest.model_validate(
        {
            "topic": "Responding correctly to 1. e4",
            "lessonShape": "practice_heavy",
        }
    )
    context = RuntimeContext.create(
        operation_name="session_generate",
        app_context=AppContext(product="homeschool-v2", surface="today"),
        presentation_context=PresentationContext(),
        user_authored_context=UserAuthoredContext(),
    )
    raw_artifact = _lesson_artifact("practice_heavy")
    raw_artifact["blocks"][0]["type"] = "practice_heavy"

    preview = SessionGenerateSkill().build_validation_retry_preview(
        payload=payload,
        context=context,
        raw_artifact=raw_artifact,
        error=ValueError("bad block type"),
    )

    assert "Every blocks[].type must be one of" in preview.user_prompt
    assert "Never put lesson_shape slugs" in preview.user_prompt
    assert "guided_practice or independent_practice" in preview.user_prompt
    assert "Every visual_aids[].url must be copied exactly" in preview.user_prompt
    assert "Do not invent, generate, guess, rewrite, or use placeholder image URLs." in preview.user_prompt


def test_session_generate_prompt_preview_adds_script_first_constraints():
    payload = SessionPlanGenerationRequest.model_validate(
        {
            "topic": "Reluctant writer script",
            "objectives": ["Help the parent read prompts almost verbatim."],
        }
    )

    preview = SessionGenerateSkill().build_prompt_preview(
        payload,
        RuntimeContext.create(
            operation_name="session_generate",
            app_context=AppContext(product="homeschool-v2", surface="today"),
            presentation_context=PresentationContext(),
            user_authored_context=UserAuthoredContext(
                parent_goal="Tell me exactly what to say.",
                special_constraints=["Keep the script concise and calm."],
            ),
        ),
    )

    assert "script-first request" in preview.user_prompt
    assert "almost verbatim" in preview.user_prompt
    assert "about 15 minutes" in preview.user_prompt


def test_session_generate_without_resolved_timing_uses_route_item_minutes():
    payload = SessionPlanGenerationRequest.model_validate(
        {
            "topic": "Week plan day 1",
            "routeItems": [
                {
                    "title": "Read chapter 2",
                    "subject": "Science",
                    "estimatedMinutes": 12,
                    "objective": "Read chapter 2",
                    "lessonLabel": "Day 1",
                },
                {
                    "title": "Answer 1-4",
                    "subject": "Science",
                    "estimatedMinutes": 8,
                    "objective": "Answer the questions",
                    "lessonLabel": "Day 1",
                },
            ],
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

    assert "Total time: 20 minutes" in preview.user_prompt


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


def test_openai_structured_output_uses_json_mode(monkeypatch, tmp_path: Path):
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
    assert fake_client.structured_output_method == "json_mode"


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
