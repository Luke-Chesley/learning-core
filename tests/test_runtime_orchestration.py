from __future__ import annotations

from pathlib import Path

import learning_core.runtime.engine as engine_module
from learning_core.runtime.engine import AgentEngine
from learning_core.runtime.providers import ModelRuntime
from learning_core.skills.catalog import build_skill_registry


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


def test_execute_generate_from_source_chains_source_interpret_into_bounded_plan(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("LEARNING_CORE_LOG_DIR", str(tmp_path / "logs"))

    def fake_build_model_runtime(*, task_name: str, **_kwargs):
        if task_name == "source_interpret":
            artifact = {
                "sourceKind": "weekly_assignments",
                "suggestedTitle": "Week plan: Fractions and decimals",
                "confidence": "high",
                "recommendedHorizon": "current_week",
                "assumptions": [
                    "The source appears to describe the current week only.",
                ],
                "detectedChunks": [
                    "Monday: fractions practice",
                    "Wednesday: decimal review",
                ],
                "followUpQuestion": None,
                "needsConfirmation": False,
            }
        else:
            artifact = {
                "title": "Week plan: Fractions and decimals",
                "description": "A bounded math week plan.",
                "subjects": ["Math"],
                "horizon": "current_week",
                "rationale": ["The source is a short current-week assignment list."],
                "document": {
                    "Math": {
                        "Week plan: Fractions and decimals": [
                            "Fractions practice",
                            "Decimal review",
                        ]
                    }
                },
                "units": [
                    {
                        "title": "Week plan: Fractions and decimals",
                        "description": "A short plan from the source.",
                        "estimatedWeeks": 1,
                        "estimatedSessions": 2,
                        "lessons": [
                            {
                                "title": "Fractions practice",
                                "description": "Work the first assignment.",
                                "subject": "Math",
                                "estimatedMinutes": 35,
                                "materials": [],
                                "objectives": ["Practice fractions"],
                                "linkedSkillTitles": ["Fractions practice"],
                            },
                            {
                                "title": "Decimal review",
                                "description": "Work the second assignment.",
                                "subject": "Math",
                                "estimatedMinutes": 35,
                                "materials": [],
                                "objectives": ["Review decimals"],
                                "linkedSkillTitles": ["Decimal review"],
                            },
                        ],
                    }
                ],
                "progression": None,
                "suggestedSessionMinutes": 35,
            }
        return ModelRuntime(
            provider="test",
            model=f"fake-{task_name}",
            client=_FakeClient(artifact),
            temperature=0.2,
            max_tokens=4096,
            max_tokens_source="test",
            provider_settings={},
        )

    monkeypatch.setattr(engine_module, "build_model_runtime", fake_build_model_runtime)

    engine = AgentEngine(build_skill_registry())
    result = engine.execute_generate_from_source(
        {
            "input": {
                "learnerName": "Nora",
                "requestedRoute": "topic",
                "inputModalities": ["file"],
                "rawText": "Monday: fractions practice\nWednesday: decimal review",
                "extractedText": "Monday: fractions practice\nWednesday: decimal review",
                "assetRefs": ["asset-1"],
                "userHorizonIntent": "auto",
                "titleCandidate": "Week 1",
            },
            "app_context": {
                "product": "homeschool-v2",
                "surface": "onboarding",
            },
        }
    )

    assert result.operation_name == "bounded_plan_generate"
    assert result.artifact["horizon"] == "current_week"
    assert result.trace.agent_trace["orchestration_profile"] == "generate_from_source"
    assert [step["operation_name"] for step in result.trace.agent_trace["substeps"]] == [
        "source_interpret",
        "bounded_plan_generate",
    ]
