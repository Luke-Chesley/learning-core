from __future__ import annotations

import json
from pathlib import Path

import pytest

import learning_core.runtime.engine as engine_module
from learning_core.contracts.operation import AppContext, PresentationContext, UserAuthoredContext
from learning_core.observability.traces import ExecutionLineage, ExecutionTrace, PromptPreview
from learning_core.contracts.source_interpret import SourceInterpretationRequest
from learning_core.runtime.context import RuntimeContext
from learning_core.runtime.engine import AgentEngine
from learning_core.runtime.errors import ContractValidationError
from learning_core.runtime.providers import ModelRuntime
from learning_core.skills.catalog import build_skill_registry
from learning_core.skills.source_interpret.scripts.main import SourceInterpretSkill


def _artifact(source_kind: str = "weekly_assignments") -> dict:
    return {
        "sourceKind": source_kind,
        "suggestedTitle": "Week plan: Fractions and decimals",
        "confidence": "high",
        "recommendedHorizon": "current_week",
        "assumptions": [
            "The source appears to describe the current week only.",
            "We should keep planning bounded to the current week.",
        ],
        "detectedChunks": [
            "Monday: fractions practice",
            "Wednesday: decimal review",
            "Friday: percent game",
        ],
        "followUpQuestion": None,
        "needsConfirmation": False,
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


class _ExplodingStructuredInvoker:
    def invoke(self, _messages):
        raise RuntimeError("Error code: 500 - provider exploded")


class _FakeTextResponse:
    def __init__(self, content: str) -> None:
        self.content = content


class _FallbackClient:
    def __init__(self, artifact: dict) -> None:
        self.artifact = artifact

    def with_structured_output(self, _output_model, **_kwargs):
        return _ExplodingStructuredInvoker()

    def invoke(self, _messages):
        return _FakeTextResponse(json.dumps(self.artifact))


def _envelope() -> dict:
    return {
        "input": {
            "learnerName": "Nora",
            "requestedRoute": "topic",
            "inputModalities": ["file"],
            "rawText": "Monday: fractions practice\nWednesday: decimal review\nFriday: percent game",
            "extractedText": "Monday: fractions practice\nWednesday: decimal review\nFriday: percent game",
            "assetRefs": ["asset-1"],
            "userHorizonIntent": "auto",
            "titleCandidate": "Week 1",
        },
        "app_context": {
            "product": "homeschool-v2",
            "surface": "onboarding",
        },
    }


def test_source_interpret_prompt_preview_lists_allowed_kinds_and_guardrails():
    payload = SourceInterpretationRequest.model_validate(_envelope()["input"])

    preview = SourceInterpretSkill().build_prompt_preview(
        payload,
        RuntimeContext.create(
            operation_name="source_interpret",
            app_context=AppContext(product="homeschool-v2", surface="onboarding"),
            presentation_context=PresentationContext(),
            user_authored_context=UserAuthoredContext(),
        ),
    )

    assert "single_day_material" in preview.system_prompt
    assert "weekly_assignments" in preview.system_prompt
    assert "sequence_outline" in preview.system_prompt
    assert "Do not generate curriculum" in preview.system_prompt
    assert "Requested route: topic" in preview.user_prompt
    assert "User horizon intent: auto" in preview.user_prompt
    assert "Do not downgrade a real outline" in preview.system_prompt
    assert "co-op days" in preview.system_prompt


def test_source_interpret_execute_rejects_invalid_source_kind(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("LEARNING_CORE_LOG_DIR", str(tmp_path / "logs"))
    monkeypatch.setattr(
        engine_module,
        "build_model_runtime",
        lambda **_kwargs: ModelRuntime(
            provider="test",
            model="fake-source-interpret",
            client=_FakeClient(_artifact(source_kind="full_curriculum")),
            temperature=0.2,
            max_tokens=2048,
            max_tokens_source="test",
            provider_settings={},
        ),
    )

    engine = AgentEngine(build_skill_registry())

    with pytest.raises(ContractValidationError):
        engine.execute("source_interpret", _envelope())


def test_source_interpret_execute_accepts_valid_artifact(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("LEARNING_CORE_LOG_DIR", str(tmp_path / "logs"))
    monkeypatch.setattr(
        engine_module,
        "build_model_runtime",
        lambda **_kwargs: ModelRuntime(
            provider="test",
            model="fake-source-interpret",
            client=_FakeClient(_artifact()),
            temperature=0.2,
            max_tokens=2048,
            max_tokens_source="test",
            provider_settings={},
        ),
    )

    engine = AgentEngine(build_skill_registry())
    result = engine.execute("source_interpret", _envelope())

    assert result.artifact["sourceKind"] == "weekly_assignments"
    assert result.artifact["recommendedHorizon"] == "current_week"


def test_source_interpret_falls_back_to_text_json_on_retryable_provider_error(
    monkeypatch, tmp_path: Path
):
    monkeypatch.setenv("LEARNING_CORE_LOG_DIR", str(tmp_path / "logs"))
    monkeypatch.setattr(
        engine_module,
        "build_model_runtime",
        lambda **_kwargs: ModelRuntime(
            provider="openai",
            model="fake-source-interpret",
            client=_FallbackClient(_artifact()),
            temperature=0.2,
            max_tokens=2048,
            max_tokens_source="test",
            provider_settings={},
        ),
    )

    engine = AgentEngine(build_skill_registry())
    result = engine.execute("source_interpret", _envelope())

    assert result.artifact["sourceKind"] == "weekly_assignments"
    assert result.artifact["recommendedHorizon"] == "current_week"
    assert result.trace.agent_trace is not None
    assert result.trace.agent_trace["structured_output_fallback"]["strategy"] == "text_json"


def test_generate_from_source_routes_sequence_outline_to_outline(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("LEARNING_CORE_LOG_DIR", str(tmp_path / "logs"))
    engine = AgentEngine(build_skill_registry())

    captured_requests: list[tuple[str, dict]] = []
    bounded_response = engine_module.OperationExecuteResponse(
        operation_name="bounded_plan_generate",
        artifact={
            "title": "Messy outline week",
            "description": "Bounded week plan",
            "subjects": ["History"],
            "horizon": "current_week",
            "rationale": ["Preserve the messy outline as a bounded week."],
            "document": {"History": {"Week": ["Lesson 1"]}},
            "units": [
                {
                    "title": "Week",
                    "description": "Week",
                    "lessons": [{"title": "Lesson 1", "description": "Desc"}],
                }
            ],
            "progression": None,
            "suggestedSessionMinutes": 20,
        },
        lineage=ExecutionLineage(
            operation_name="bounded_plan_generate",
            skill_name="bounded_plan_generate",
            skill_version="test",
            provider="test",
            model="test",
        ),
        trace=ExecutionTrace(
            request_id="req-123",
            operation_name="bounded_plan_generate",
            allowed_tools=[],
            prompt_preview=PromptPreview(system_prompt="", user_prompt=""),
            request_envelope=engine_module.OperationEnvelope.model_validate(
                {
                    "input": {"topic": "messy outline"},
                    "app_context": {"product": "homeschool-v2", "surface": "onboarding"},
                }
            ),
        ),
        prompt_preview=PromptPreview(system_prompt="", user_prompt=""),
    )

    def fake_execute(self, operation_name: str, envelope_data: dict):
        captured_requests.append((operation_name, envelope_data))
        if operation_name == "source_interpret":
            return engine_module.OperationExecuteResponse(
                operation_name="source_interpret",
                artifact={
                    "sourceKind": "sequence_outline",
                    "suggestedTitle": "Mangled outline",
                    "confidence": "medium",
                    "recommendedHorizon": "current_week",
                    "assumptions": ["Keep the copied outline structure visible."],
                    "detectedChunks": ["Chapter 4", "co-op Thursday"],
                    "followUpQuestion": None,
                    "needsConfirmation": False,
                },
                lineage=ExecutionLineage(
                    operation_name="source_interpret",
                    skill_name="source_interpret",
                    skill_version="test",
                    provider="test",
                    model="test",
                ),
                trace=ExecutionTrace(
                    request_id="req-123",
                    operation_name="source_interpret",
                    allowed_tools=[],
                    prompt_preview=PromptPreview(system_prompt="", user_prompt=""),
                    request_envelope=engine_module.OperationEnvelope.model_validate(
                        {
                            "input": _envelope()["input"],
                            "app_context": {"product": "homeschool-v2", "surface": "onboarding"},
                        }
                    ),
                ),
                prompt_preview=PromptPreview(system_prompt="", user_prompt=""),
            )
        if operation_name == "bounded_plan_generate":
            return bounded_response
        raise AssertionError(f"Unexpected operation: {operation_name}")

    monkeypatch.setattr(engine_module.AgentEngine, "execute", fake_execute, raising=True)

    result = AgentEngine(build_skill_registry()).execute_generate_from_source(_envelope())

    bounded_call = next(data for name, data in captured_requests if name == "bounded_plan_generate")
    assert bounded_call["input"]["requestedRoute"] == "outline"
    assert bounded_call["input"]["routedRoute"] == "outline"
    assert result.artifact["horizon"] == "current_week"
