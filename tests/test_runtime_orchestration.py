from __future__ import annotations

from pathlib import Path

import learning_core.runtime.engine as engine_module
from learning_core.runtime.engine import AgentEngine
from learning_core.runtime.providers import ModelRuntime
from learning_core.skills.catalog import build_skill_registry


class _FakeStructuredInvoker:
    def __init__(self, artifact: dict, captured_messages: list | None = None) -> None:
        self.artifact = artifact
        self.captured_messages = captured_messages

    def invoke(self, messages):
        if self.captured_messages is not None:
            self.captured_messages.extend(messages)
        return self.artifact


class _FakeClient:
    def __init__(self, artifact: dict, captured_messages: list | None = None) -> None:
        self.artifact = artifact
        self.captured_messages = captured_messages

    def with_structured_output(self, _output_model, **_kwargs):
        return _FakeStructuredInvoker(self.artifact, self.captured_messages)


def test_execute_generate_from_source_chains_new_interpretation_into_bounded_plan(
    monkeypatch, tmp_path: Path
):
    monkeypatch.setenv("LEARNING_CORE_LOG_DIR", str(tmp_path / "logs"))
    captured_bounded_messages: list = []

    def fake_build_model_runtime(*, task_name: str, **_kwargs):
        if task_name == "source_interpret":
            artifact = {
                "sourceKind": "comprehensive_source",
                "entryStrategy": "explicit_range",
                "entryLabel": "pages 1-12",
                "continuationMode": "sequential",
                "suggestedTitle": "Workbook launch",
                "confidence": "high",
                "recommendedHorizon": "few_days",
                "assumptions": [
                    "Parent explicitly asked to use pages 1-12 only.",
                ],
                "detectedChunks": [
                    "pages 1-12",
                    "later chapters",
                ],
                "followUpQuestion": None,
                "needsConfirmation": False,
            }
        else:
            artifact = {
                "title": "Workbook launch",
                "description": "A bounded opening plan.",
                "subjects": ["Math"],
                "horizon": "few_days",
                "rationale": ["Stay inside the explicit assigned range."],
                "document": {
                    "Math": {
                        "Pages 1-12": [
                            "Warm-up from page 1",
                            "Guided practice from pages 2-6",
                            "Independent practice from pages 7-12",
                        ]
                    }
                },
                "units": [
                    {
                        "title": "Pages 1-12",
                        "description": "Bounded opening range",
                        "estimatedWeeks": 1,
                        "estimatedSessions": 3,
                        "lessons": [
                            {
                                "title": "Warm-up from page 1",
                                "description": "Open the workbook safely.",
                                "subject": "Math",
                                "estimatedMinutes": 25,
                                "materials": [],
                                "objectives": ["Begin the range"],
                                "linkedSkillTitles": ["Pages 1-12"],
                            },
                            {
                                "title": "Guided practice from pages 2-6",
                                "description": "Continue the bounded opening.",
                                "subject": "Math",
                                "estimatedMinutes": 30,
                                "materials": [],
                                "objectives": ["Practice the middle chunk"],
                                "linkedSkillTitles": ["Pages 1-12"],
                            },
                            {
                                "title": "Independent practice from pages 7-12",
                                "description": "Finish the explicit opening range.",
                                "subject": "Math",
                                "estimatedMinutes": 30,
                                "materials": [],
                                "objectives": ["Finish the range"],
                                "linkedSkillTitles": ["Pages 1-12"],
                            },
                        ],
                    }
                ],
                "progression": None,
                "suggestedSessionMinutes": 30,
            }
        return ModelRuntime(
            provider="test",
            model=f"fake-{task_name}",
            client=_FakeClient(
                artifact,
                captured_bounded_messages if task_name == "bounded_plan_generate" else None,
            ),
            temperature=0.2,
            max_tokens=4096,
            max_tokens_source="test",
            provider_settings={},
        )

    monkeypatch.setattr(engine_module, "build_model_runtime", fake_build_model_runtime)

    result = AgentEngine(build_skill_registry()).execute_generate_from_source(
        {
            "input": {
                "learnerName": "Nora",
                "requestedRoute": "topic",
                "inputModalities": ["file"],
                "rawText": "Workbook pages 1-12 only",
                "extractedText": "Workbook pages 1-12 only",
                "assetRefs": ["asset-1"],
                "titleCandidate": "Workbook launch",
            },
            "app_context": {
                "product": "homeschool-v2",
                "surface": "onboarding",
            },
        }
    )

    assert result.operation_name == "bounded_plan_generate"
    assert result.artifact["horizon"] == "few_days"
    assert result.trace.agent_trace["orchestration_profile"] == "generate_from_source"
    assert [step["operation_name"] for step in result.trace.agent_trace["substeps"]] == [
        "source_interpret",
        "bounded_plan_generate",
    ]
    bounded_prompt = captured_bounded_messages[1].content
    assert "Source kind: comprehensive_source" in bounded_prompt
    assert "Entry strategy: explicit_range" in bounded_prompt
    assert "Entry label: pages 1-12" in bounded_prompt
    assert "Continuation mode: sequential" in bounded_prompt
    assert "Chosen horizon: few_days" in bounded_prompt
    assert "Detected chunks:" in bounded_prompt
    assert "Assumptions:" in bounded_prompt
    assert "\"Parent explicitly asked to use pages 1-12 only.\"" in bounded_prompt
