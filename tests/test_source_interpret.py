from __future__ import annotations

import json
from pathlib import Path

import pytest

import learning_core.runtime.engine as engine_module
from learning_core.contracts.operation import AppContext, PresentationContext, UserAuthoredContext
from learning_core.contracts.source_interpret import SourceInterpretationRequest
from learning_core.observability.traces import ExecutionLineage, ExecutionTrace, PromptPreview
from learning_core.runtime.context import RuntimeContext
from learning_core.runtime.engine import AgentEngine
from learning_core.runtime.errors import ContractValidationError
from learning_core.runtime.providers import ModelRuntime
from learning_core.skills.catalog import build_skill_registry
from learning_core.skills.source_interpret.scripts.main import SourceInterpretSkill


def _artifact(
    *,
    source_kind: str = "timeboxed_plan",
    entry_strategy: str = "timebox_start",
    entry_label: str | None = "week 1",
    continuation_mode: str = "timebox",
    recommended_horizon: str = "one_week",
    **overrides,
) -> dict:
    artifact = {
        "sourceKind": source_kind,
        "entryStrategy": entry_strategy,
        "entryLabel": entry_label,
        "continuationMode": continuation_mode,
        "suggestedTitle": "Week plan: Fractions and decimals",
        "confidence": "high",
        "recommendedHorizon": recommended_horizon,
        "assumptions": [
            "The source appears to describe an initial week only.",
            "The safest start is to keep the opening bounded.",
        ],
        "detectedChunks": [
            "Monday: fractions practice",
            "Wednesday: decimal review",
            "Friday: percent game",
        ],
        "followUpQuestion": None,
        "needsConfirmation": False,
    }
    artifact.update(overrides)
    return artifact


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

    def invoke(self, _messages):
        return _FakeTextResponse(json.dumps(self.artifact))


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


class _RepairFallbackClient:
    def __init__(self, structured_artifact: dict, repaired_artifact: dict) -> None:
        self.structured_artifact = structured_artifact
        self.repaired_artifact = repaired_artifact

    def with_structured_output(self, _output_model, **_kwargs):
        return _FakeStructuredInvoker(self.structured_artifact)

    def invoke(self, _messages):
        return _FakeTextResponse(json.dumps(self.repaired_artifact))


def _envelope() -> dict:
    return {
        "input": {
            "learnerName": "Nora",
            "requestedRoute": "topic",
            "inputModalities": ["file"],
            "rawText": "Monday: fractions practice\nWednesday: decimal review\nFriday: percent game",
            "extractedText": "Monday: fractions practice\nWednesday: decimal review\nFriday: percent game",
            "assetRefs": ["asset-1"],
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
            "titleCandidate": "Week 1",
        },
        "app_context": {
            "product": "homeschool-v2",
            "surface": "onboarding",
        },
    }


def test_source_interpret_prompt_preview_lists_new_taxonomy_and_guardrails():
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

    assert "bounded_material" in preview.system_prompt
    assert "timeboxed_plan" in preview.system_prompt
    assert "structured_sequence" in preview.system_prompt
    assert "comprehensive_source" in preview.system_prompt
    assert "shell_request" in preview.system_prompt
    assert "entryStrategy" in preview.system_prompt
    assert "continuationMode" in preview.system_prompt
    assert "Do not treat a whole book as" in preview.system_prompt
    assert "single_day_material" not in preview.system_prompt
    assert "weekly_assignments" not in preview.system_prompt
    assert "sequence_outline" not in preview.system_prompt
    assert "manual_shell" not in preview.system_prompt
    assert "today" not in preview.system_prompt
    assert "tomorrow" not in preview.system_prompt
    assert "next_few_days" not in preview.system_prompt
    assert "current_week" not in preview.system_prompt
    assert "starter_week" not in preview.system_prompt
    assert "Requested route: topic" in preview.user_prompt
    assert "Source packages:" in preview.user_prompt
    assert "Week 1 upload" in preview.user_prompt
    assert "Attached source files:" in preview.user_prompt
    assert "week-1.pdf" in preview.user_prompt
    assert "User horizon intent" not in preview.user_prompt
    assert "userHorizonIntent" not in preview.user_prompt


def test_source_interpret_builds_openai_file_message_blocks():
    payload = SourceInterpretationRequest.model_validate(_envelope()["input"])
    content = SourceInterpretSkill().build_user_message_content(
        payload,
        RuntimeContext.create(
            operation_name="source_interpret",
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
        "file_url": "https://example.com/week-1.pdf",
    }


def test_source_interpret_execute_rejects_invalid_source_kind(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("LEARNING_CORE_LOG_DIR", str(tmp_path / "logs"))
    monkeypatch.setattr(
        engine_module,
        "build_model_runtime",
        lambda **_kwargs: ModelRuntime(
            provider="test",
            model="fake-source-interpret",
            client=_FakeClient({**_artifact(), "sourceKind": "full_curriculum"}),
            temperature=0.2,
            max_tokens=2048,
            max_tokens_source="test",
            provider_settings={},
        ),
    )

    with pytest.raises(ContractValidationError):
        AgentEngine(build_skill_registry()).execute("source_interpret", _envelope())


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

    result = AgentEngine(build_skill_registry()).execute("source_interpret", _envelope())

    assert result.artifact["sourceKind"] == "timeboxed_plan"
    assert result.artifact["entryStrategy"] == "timebox_start"
    assert result.artifact["continuationMode"] == "timebox"
    assert result.artifact["recommendedHorizon"] == "one_week"


def test_source_interpret_execute_accepts_comprehensive_source_whole_book_artifact(
    monkeypatch, tmp_path: Path
):
    monkeypatch.setenv("LEARNING_CORE_LOG_DIR", str(tmp_path / "logs"))
    monkeypatch.setattr(
        engine_module,
        "build_model_runtime",
        lambda **_kwargs: ModelRuntime(
            provider="test",
            model="fake-source-interpret",
            client=_FakeClient(
                _artifact(
                    source_kind="comprehensive_source",
                    entry_strategy="section_start",
                    entry_label="chapter 1",
                    continuation_mode="sequential",
                    recommended_horizon="one_week",
                    suggestedTitle="Kids in the Kitchen",
                    assumptions=[
                        "This is a whole book, so launch from chapter 1 and keep the rest for continuation.",
                    ],
                    detectedChunks=["chapter 1", "chapter 2", "appendix"],
                )
            ),
            temperature=0.2,
            max_tokens=2048,
            max_tokens_source="test",
            provider_settings={},
        ),
    )

    result = AgentEngine(build_skill_registry()).execute("source_interpret", _envelope())

    assert result.artifact["sourceKind"] == "comprehensive_source"
    assert result.artifact["entryStrategy"] == "section_start"
    assert result.artifact["entryLabel"] == "chapter 1"
    assert result.artifact["continuationMode"] == "sequential"
    assert result.artifact["recommendedHorizon"] == "one_week"


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

    result = AgentEngine(build_skill_registry()).execute("source_interpret", _envelope())

    assert result.artifact["sourceKind"] == "timeboxed_plan"
    assert result.artifact["recommendedHorizon"] == "one_week"
    assert result.trace.agent_trace is not None
    assert result.trace.agent_trace["structured_output_fallback"]["strategy"] == "text_json"


def test_source_interpret_repairs_missing_required_fields(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("LEARNING_CORE_LOG_DIR", str(tmp_path / "logs"))
    invalid_artifact = {
        "sourceKind": "comprehensive_source",
        "suggestedTitle": "Kids in the Kitchen",
        "confidence": "medium",
        "assumptions": [],
        "detectedChunks": [],
    }
    monkeypatch.setattr(
        engine_module,
        "build_model_runtime",
        lambda **_kwargs: ModelRuntime(
            provider="openai",
            model="fake-source-interpret",
            client=_FakeClient(invalid_artifact),
            temperature=0.2,
            max_tokens=2048,
            max_tokens_source="test",
            provider_settings={},
        ),
    )

    result = AgentEngine(build_skill_registry()).execute("source_interpret", _envelope())

    assert result.artifact["sourceKind"] == "comprehensive_source"
    assert result.artifact["entryStrategy"] == "section_start"
    assert result.artifact["continuationMode"] == "sequential"
    assert result.artifact["recommendedHorizon"] == "one_week"
    assert result.artifact["detectedChunks"] == [
        "Monday: fractions practice",
        "Wednesday: decimal review",
        "Friday: percent game",
    ]
    assert result.trace.agent_trace is not None
    assert result.trace.agent_trace["structured_output_fallback"]["strategy"] == "deterministic_repair"


def test_source_interpret_retries_with_repair_prompt_on_validation_error(
    monkeypatch, tmp_path: Path
):
    monkeypatch.setenv("LEARNING_CORE_LOG_DIR", str(tmp_path / "logs"))
    structured_artifact = {
        "suggestedTitle": "Teach chess",
        "confidence": "high",
        "assumptions": [],
        "detectedChunks": [],
        "needsConfirmation": False,
    }
    monkeypatch.setattr(
        engine_module,
        "build_model_runtime",
        lambda **_kwargs: ModelRuntime(
            provider="openai",
            model="fake-source-interpret",
            client=_RepairFallbackClient(
                structured_artifact,
                _artifact(
                    source_kind="topic_seed",
                    entry_strategy="scaffold_only",
                    entry_label=None,
                    continuation_mode="manual_review",
                    recommended_horizon="starter_module",
                ),
            ),
            temperature=0.2,
            max_tokens=2048,
            max_tokens_source="test",
            provider_settings={},
        ),
    )

    result = AgentEngine(build_skill_registry()).execute("source_interpret", _envelope())

    assert result.artifact["sourceKind"] == "topic_seed"
    assert result.artifact["entryStrategy"] == "scaffold_only"
    assert result.artifact["continuationMode"] == "manual_review"
    assert result.artifact["recommendedHorizon"] == "starter_module"
    assert result.trace.agent_trace is not None
    assert result.trace.agent_trace["structured_output_fallback"]["strategy"] == "validation_repair"


def test_generate_from_source_threads_new_interpretation_fields_into_curriculum_generate(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("LEARNING_CORE_LOG_DIR", str(tmp_path / "logs"))
    captured_requests: list[tuple[str, dict]] = []
    curriculum_response = engine_module.OperationExecuteResponse(
        operation_name="curriculum_generate",
        artifact={
            "source": {
                "title": "Kids in the Kitchen",
                "description": "A source-entry launch",
                "subjects": ["Life Skills"],
                "gradeLevels": [],
                "academicYear": None,
                "summary": "Start with chapter 1 only.",
                "teachingApproach": "Hands-on cooking routines",
                "successSignals": [],
                "parentNotes": [],
                "rationale": ["Honor the explicit chapter 1 request."],
            },
            "intakeSummary": "Generated from source entry.",
            "pacing": {
                "totalWeeks": 1,
                "sessionsPerWeek": 3,
                "sessionMinutes": 25,
                "totalSessions": 3,
                "coverageStrategy": "Stay inside the initial launch slice.",
                "coverageNotes": [],
            },
            "launchPlan": {
                "recommendedHorizon": "one_week",
                "openingLessonCount": 1,
                "scopeSummary": "Start with chapter 1 only and keep the rest for later.",
                "initialSliceUsed": True,
                "initialSliceLabel": "chapter 1",
                "entryStrategy": "explicit_range",
                "entryLabel": "chapter 1",
                "continuationMode": "sequential",
            },
            "document": {"Life Skills": {"Chapter 1": ["Kitchen setup"]}},
            "units": [
                {
                    "title": "Chapter 1",
                    "description": "Source-entry launch unit",
                    "lessons": [{"title": "Kitchen setup", "description": "Get ready to cook."}],
                }
            ],
            "progression": None,
        },
        lineage=ExecutionLineage(
            operation_name="curriculum_generate",
            skill_name="curriculum_generate",
            skill_version="test",
            provider="test",
            model="test",
        ),
        trace=ExecutionTrace(
            request_id="req-123",
            operation_name="curriculum_generate",
            allowed_tools=[],
            prompt_preview=PromptPreview(system_prompt="", user_prompt=""),
            request_envelope=engine_module.OperationEnvelope.model_validate(
                {
                    "input": {"topic": "kitchen"},
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
                    "sourceKind": "comprehensive_source",
                    "entryStrategy": "explicit_range",
                    "entryLabel": "chapter 1",
                    "continuationMode": "sequential",
                    "suggestedTitle": "Kids in the Kitchen",
                    "confidence": "high",
                    "recommendedHorizon": "one_week",
                    "assumptions": ["Honor the explicit chapter 1 request."],
                    "detectedChunks": ["chapter 1", "chapter 2"],
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
        if operation_name == "curriculum_generate":
            return curriculum_response
        raise AssertionError(f"Unexpected operation: {operation_name}")

    monkeypatch.setattr(engine_module.AgentEngine, "execute", fake_execute, raising=True)

    result = AgentEngine(build_skill_registry()).execute_generate_from_source(_envelope())

    curriculum_call = next(data for name, data in captured_requests if name == "curriculum_generate")
    assert curriculum_call["input"]["requestMode"] == "source_entry"
    assert curriculum_call["input"]["requestedRoute"] == "topic"
    assert curriculum_call["input"]["routedRoute"] == "outline"
    assert curriculum_call["input"]["sourceKind"] == "comprehensive_source"
    assert curriculum_call["input"]["entryStrategy"] == "explicit_range"
    assert curriculum_call["input"]["entryLabel"] == "chapter 1"
    assert curriculum_call["input"]["continuationMode"] == "sequential"
    assert curriculum_call["input"]["recommendedHorizon"] == "one_week"
    assert curriculum_call["input"]["titleCandidate"] == "Week 1"
    assert curriculum_call["input"]["detectedChunks"] == ["chapter 1", "chapter 2"]
    assert curriculum_call["input"]["assumptions"] == ["Honor the explicit chapter 1 request."]
    assert result.operation_name == "curriculum_generate"
    assert result.artifact["launchPlan"]["recommendedHorizon"] == "one_week"
