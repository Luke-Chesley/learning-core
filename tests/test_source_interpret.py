from __future__ import annotations

from pathlib import Path

import pytest

import learning_core.runtime.engine as engine_module
from learning_core.contracts.operation import AppContext, PresentationContext, UserAuthoredContext
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
