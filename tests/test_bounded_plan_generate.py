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


def _artifact(title: str = "Current week fractions plan") -> dict:
    return {
        "title": title,
        "description": "A bounded math plan for the current week.",
        "subjects": ["Math"],
        "horizon": "current_week",
        "rationale": [
            "The source clearly names three weekday tasks.",
            "The scope stays inside the current week.",
        ],
        "document": {
            "Math": {
                "Current week fractions and decimals": [
                    "Fractions practice",
                    "Decimal review",
                    "Percent game",
                ]
            }
        },
        "units": [
            {
                "title": "Current week fractions and decimals",
                "description": "A short week plan built from the provided assignments.",
                "estimatedWeeks": 1,
                "estimatedSessions": 3,
                "lessons": [
                    {
                        "title": "Fractions practice",
                        "description": "Work through the Monday fractions task.",
                        "subject": "Math",
                        "estimatedMinutes": 35,
                        "materials": [],
                        "objectives": ["Practice fraction reasoning"],
                        "linkedSkillTitles": ["Fractions practice"],
                    },
                    {
                        "title": "Decimal review",
                        "description": "Review decimals in the middle of the week.",
                        "subject": "Math",
                        "estimatedMinutes": 35,
                        "materials": [],
                        "objectives": ["Review decimal understanding"],
                        "linkedSkillTitles": ["Decimal review"],
                    },
                    {
                        "title": "Percent game",
                        "description": "Use a short game to rehearse percents.",
                        "subject": "Math",
                        "estimatedMinutes": 35,
                        "materials": [],
                        "objectives": ["Practice percent thinking"],
                        "linkedSkillTitles": ["Percent game"],
                    },
                ],
            }
        ],
        "progression": None,
        "suggestedSessionMinutes": 35,
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
            "routedRoute": "weekly_plan",
            "sourceKind": "weekly_assignments",
            "chosenHorizon": "current_week",
            "sourceText": "Monday: fractions practice\nWednesday: decimal review\nFriday: percent game",
            "sourcePackages": [
                {
                    "id": "ipkg-1",
                    "title": "Week 1 upload",
                    "modality": "file",
                    "summary": "File · Monday fractions practice",
                    "extractionStatus": "ready",
                    "assetCount": 1,
                    "assetIds": ["asset-1"],
                    "detectedChunks": ["Monday: fractions practice"],
                    "sourceFingerprint": "fp-1",
                }
            ],
            "sourceFiles": [
                {
                    "assetId": "asset-1",
                    "packageId": "ipkg-1",
                    "title": "Week 1 upload",
                    "modality": "pdf",
                    "fileName": "week-1.pdf",
                    "mimeType": "application/pdf",
                    "fileUrl": "https://example.com/week-1.pdf",
                }
            ],
            "titleCandidate": "Monday/Wednesday/Friday math practice plan",
            "detectedChunks": [
                "Monday: fractions practice",
                "Wednesday: decimal review",
                "Friday: percent game",
            ],
            "assumptions": [
                "The source is a short multi-day assignment list.",
                "We should keep the plan inside the current week.",
            ],
        },
        "app_context": {
            "product": "homeschool-v2",
            "surface": "onboarding",
        },
    }


def test_bounded_plan_prompt_preview_includes_guardrails():
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

    assert "today" in preview.system_prompt
    assert "current_week" in preview.system_prompt
    assert "Do not invent a semester" in preview.system_prompt
    assert "Routed route: weekly_plan" in preview.user_prompt
    assert "Chosen horizon: current_week" in preview.user_prompt
    assert "Source packages:" in preview.user_prompt
    assert "Week 1 upload" in preview.user_prompt
    assert "Attached source files:" in preview.user_prompt
    assert "week-1.pdf" in preview.user_prompt
    assert "The `document` field is required." in preview.user_prompt
    assert "subject -> unit title -> ordered lesson title list" in preview.user_prompt


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
        "type": "file",
        "file": {
            "file_url": "https://example.com/week-1.pdf",
            "filename": "week-1.pdf",
        },
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

    engine = AgentEngine(build_skill_registry())

    with pytest.raises(ContractValidationError):
        engine.execute("bounded_plan_generate", _envelope())


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

    engine = AgentEngine(build_skill_registry())
    result = engine.execute("bounded_plan_generate", _envelope())

    assert result.artifact["horizon"] == "current_week"
    assert result.artifact["units"][0]["lessons"][0]["title"] == "Fractions practice"


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

    engine = AgentEngine(build_skill_registry())
    result = engine.execute("bounded_plan_generate", _envelope())

    assert result.artifact["document"] == {
        "Math": {
            "Current week fractions and decimals": [
                "Fractions practice",
                "Decimal review",
                "Percent game",
            ]
        }
    }
