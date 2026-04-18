from __future__ import annotations

from pathlib import Path

import pytest

import learning_core.runtime.engine as engine_module
from learning_core.contracts.bounded_plan import BoundedPlanGenerationRequest
from learning_core.contracts.operation import AppContext, PresentationContext, UserAuthoredContext
from learning_core.runtime.context import RuntimeContext
from learning_core.runtime.engine import AgentEngine
from learning_core.runtime.errors import ContractValidationError
from learning_core.runtime.providers import ModelRuntime
from learning_core.skills.bounded_plan_generate.scripts.main import BoundedPlanGenerateSkill
from learning_core.skills.catalog import build_skill_registry


def _interpretation() -> dict:
    return {
        "sourceKind": "comprehensive_source",
        "entryStrategy": "explicit_range",
        "entryLabel": "chapter 1",
        "continuationMode": "sequential",
        "suggestedTitle": "Kids in the Kitchen",
        "confidence": "high",
        "recommendedHorizon": "few_days",
        "assumptions": [
            "Stay inside the explicit chapter 1 range.",
        ],
        "detectedChunks": [
            "chapter 1",
            "chapter 2",
        ],
        "followUpQuestion": None,
        "needsConfirmation": False,
    }


def _artifact(title: str = "Kids in the Kitchen") -> dict:
    return {
        "title": title,
        "description": "A bounded life-skills opening plan.",
        "subjects": ["Life Skills"],
        "horizon": "few_days",
        "rationale": [
            "Use only the explicit chapter 1 opening range.",
            "Keep the launch bounded before later continuation.",
        ],
        "document": {
            "Life Skills": {
                "Chapter 1": [
                    "Kitchen setup",
                    "Tools and safety",
                    "First simple prep",
                ]
            }
        },
        "units": [
            {
                "title": "Chapter 1",
                "description": "A short opening range built from the explicit entry.",
                "estimatedWeeks": 1,
                "estimatedSessions": 3,
                "lessons": [
                    {
                        "title": "Kitchen setup",
                        "description": "Open with the setup lesson.",
                        "subject": "Life Skills",
                        "estimatedMinutes": 30,
                        "materials": [],
                        "objectives": ["Identify the kitchen setup basics"],
                        "linkedSkillTitles": ["Kitchen setup"],
                    },
                    {
                        "title": "Tools and safety",
                        "description": "Continue inside the same opening range.",
                        "subject": "Life Skills",
                        "estimatedMinutes": 30,
                        "materials": [],
                        "objectives": ["Practice kitchen safety steps"],
                        "linkedSkillTitles": ["Tools and safety"],
                    },
                    {
                        "title": "First simple prep",
                        "description": "Close the opening range with a simple task.",
                        "subject": "Life Skills",
                        "estimatedMinutes": 30,
                        "materials": [],
                        "objectives": ["Complete the first bounded prep task"],
                        "linkedSkillTitles": ["First simple prep"],
                    },
                ],
            }
        ],
        "progression": None,
        "suggestedSessionMinutes": 30,
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
            "learnerName": "Iris",
            "requestedRoute": "topic",
            "routedRoute": "outline",
            "sourceKind": "comprehensive_source",
            "entryStrategy": "explicit_range",
            "entryLabel": "chapter 1",
            "continuationMode": "sequential",
            "chosenHorizon": "few_days",
            "sourceText": "Chapter 1: Kitchen setup\nChapter 2: Breakfast basics",
            "sourcePackages": [
                {
                    "id": "ipkg-1",
                    "title": "Cooking workbook",
                    "modality": "file",
                    "summary": "Workbook pages for kitchen routines",
                    "extractionStatus": "ready",
                    "assetCount": 1,
                    "assetIds": ["asset-1"],
                    "detectedChunks": ["chapter 1"],
                    "sourceFingerprint": "fp-1",
                }
            ],
            "sourceFiles": [
                {
                    "assetId": "asset-1",
                    "packageId": "ipkg-1",
                    "title": "Cooking workbook",
                    "modality": "pdf",
                    "fileName": "cooking-workbook.pdf",
                    "mimeType": "application/pdf",
                    "fileUrl": "https://example.com/cooking-workbook.pdf",
                }
            ],
            "titleCandidate": "Workbook launch",
            "detectedChunks": ["chapter 1", "chapter 2"],
            "assumptions": ["Stay inside the explicit chapter 1 range."],
        },
        "app_context": {
            "product": "homeschool-v2",
            "surface": "onboarding",
        },
    }


def test_bounded_plan_prompt_preview_threads_explicit_source_fields():
    payload = BoundedPlanGenerationRequest.model_validate(_envelope()["input"])

    preview = BoundedPlanGenerateSkill().build_prompt_preview(
        payload,
        RuntimeContext.create(
            operation_name="bounded_plan_generate",
            app_context=AppContext(product="homeschool-v2", surface="onboarding"),
            presentation_context=PresentationContext(),
            user_authored_context=UserAuthoredContext(),
        ),
    )

    assert "single_day" in preview.system_prompt
    assert "few_days" in preview.system_prompt
    assert "starter_module" in preview.system_prompt
    assert "Requested route: topic" in preview.user_prompt
    assert "Routed route: outline" in preview.user_prompt
    assert "Source kind: comprehensive_source" in preview.user_prompt
    assert "Entry strategy: explicit_range" in preview.user_prompt
    assert "Entry label: chapter 1" in preview.user_prompt
    assert "Continuation mode: sequential" in preview.user_prompt
    assert "Chosen horizon: few_days" in preview.user_prompt
    assert "Detected chunks:" in preview.user_prompt
    assert "Assumptions:" in preview.user_prompt
    assert "Cooking workbook" in preview.user_prompt
    assert "The first lesson or day must be immediately teachable" in preview.user_prompt
    assert "If the entry strategy is `explicit_range`, stay inside that range." in preview.user_prompt


def test_bounded_plan_builds_openai_file_message_blocks():
    payload = BoundedPlanGenerationRequest.model_validate(_envelope()["input"])
    content = BoundedPlanGenerateSkill().build_user_message_content(
        payload,
        RuntimeContext.create(
            operation_name="bounded_plan_generate",
            app_context=AppContext(product="homeschool-v2", surface="onboarding"),
            presentation_context=PresentationContext(),
            user_authored_context=UserAuthoredContext(),
        ),
        provider="openai",
    )

    assert isinstance(content, list)
    assert content[0]["type"] == "text"
    assert content[1] == {
        "type": "input_file",
        "file_url": "https://example.com/cooking-workbook.pdf",
    }


def test_bounded_plan_execute_rejects_invalid_artifact(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("LEARNING_CORE_LOG_DIR", str(tmp_path / "logs"))
    monkeypatch.setattr(
        engine_module,
        "build_model_runtime",
        lambda **_kwargs: ModelRuntime(
            provider="test",
            model="fake-bounded-plan",
            client=_FakeClient({**_artifact(), "units": []}),
            temperature=0.2,
            max_tokens=4096,
            max_tokens_source="test",
            provider_settings={},
        ),
    )

    with pytest.raises(ContractValidationError):
        AgentEngine(build_skill_registry()).execute("bounded_plan_generate", _envelope())


def test_bounded_plan_execute_accepts_valid_artifact(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("LEARNING_CORE_LOG_DIR", str(tmp_path / "logs"))
    monkeypatch.setattr(
        engine_module,
        "build_model_runtime",
        lambda **_kwargs: ModelRuntime(
            provider="test",
            model="fake-bounded-plan",
            client=_FakeClient(_artifact()),
            temperature=0.2,
            max_tokens=4096,
            max_tokens_source="test",
            provider_settings={},
        ),
    )

    result = AgentEngine(build_skill_registry()).execute("bounded_plan_generate", _envelope())

    assert result.artifact["horizon"] == "few_days"
    assert result.artifact["units"][0]["title"] == "Chapter 1"
    assert result.artifact["units"][0]["lessons"][0]["title"] == "Kitchen setup"


def test_bounded_plan_execute_backfills_document_from_units(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("LEARNING_CORE_LOG_DIR", str(tmp_path / "logs"))
    artifact_without_document = _artifact()
    artifact_without_document.pop("document", None)
    monkeypatch.setattr(
        engine_module,
        "build_model_runtime",
        lambda **_kwargs: ModelRuntime(
            provider="test",
            model="fake-bounded-plan",
            client=_FakeClient(artifact_without_document),
            temperature=0.2,
            max_tokens=4096,
            max_tokens_source="test",
            provider_settings={},
        ),
    )

    result = AgentEngine(build_skill_registry()).execute("bounded_plan_generate", _envelope())

    assert result.artifact["document"] == {
        "Life Skills": {
            "Chapter 1": [
                "Kitchen setup",
                "Tools and safety",
                "First simple prep",
            ]
        }
    }
