from __future__ import annotations

import learning_core.runtime.engine as engine_module
from learning_core.observability.traces import ExecutionLineage, ExecutionTrace, PromptPreview
from learning_core.runtime.engine import AgentEngine
from learning_core.skills.catalog import build_skill_registry


def test_execute_generate_from_source_returns_curriculum_generate_result(monkeypatch):
    source_response = engine_module.OperationExecuteResponse(
        operation_name="source_interpret",
        artifact={
            "sourceKind": "comprehensive_source",
            "entryStrategy": "explicit_range",
            "entryLabel": "pages 1-12",
            "continuationMode": "sequential",
            "deliveryPattern": "skill_first",
            "suggestedTitle": "Workbook launch",
            "confidence": "high",
            "recommendedHorizon": "few_days",
            "assumptions": ["Parent explicitly asked to use pages 1-12 only."],
            "detectedChunks": ["pages 1-12", "later chapters"],
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
            request_id="req-source",
            operation_name="source_interpret",
            allowed_tools=[],
            prompt_preview=PromptPreview(system_prompt="", user_prompt=""),
            request_envelope=engine_module.OperationEnvelope.model_validate(
                {
                    "input": {"requestedRoute": "topic"},
                    "app_context": {"product": "homeschool-v2", "surface": "onboarding"},
                }
            ),
        ),
        prompt_preview=PromptPreview(system_prompt="", user_prompt=""),
    )
    curriculum_response = engine_module.OperationExecuteResponse(
        operation_name="curriculum_generate",
        artifact={
            "source": {
                "title": "Workbook launch",
                "description": "A curriculum launch from the opening pages.",
                "subjects": ["Math"],
                "gradeLevels": [],
                "academicYear": None,
                "summary": "Stay inside the explicit assigned range.",
                "teachingApproach": "Workbook-guided launch",
                "successSignals": [],
                "parentNotes": [],
                "rationale": ["Stay inside the explicit assigned range."],
            },
            "intakeSummary": "Generated from a source entry request.",
            "pacing": {
                "totalWeeks": 1,
                "sessionsPerWeek": 3,
                "sessionMinutes": 30,
                "totalSessions": 3,
                "coverageStrategy": "Launch inside the interpreted opening slice.",
                "coverageNotes": [],
            },
            "skills": [
                {
                    "skillId": "skill-1",
                    "domainTitle": "Math",
                    "strandTitle": "Pages 1-12",
                    "goalGroupTitle": "Workbook launch",
                    "title": "Warm-up from page 1",
                },
                {
                    "skillId": "skill-2",
                    "domainTitle": "Math",
                    "strandTitle": "Pages 1-12",
                    "goalGroupTitle": "Workbook launch",
                    "title": "Guided practice from pages 2-6",
                },
                {
                    "skillId": "skill-3",
                    "domainTitle": "Math",
                    "strandTitle": "Pages 1-12",
                    "goalGroupTitle": "Workbook launch",
                    "title": "Independent practice from pages 7-12",
                },
            ],
            "units": [
                {
                    "unitRef": "unit:1:pages-1-12",
                    "title": "Pages 1-12",
                    "description": "Work through the opening workbook range in order.",
                    "estimatedWeeks": 1,
                    "estimatedSessions": 3,
                    "skillIds": ["skill-1", "skill-2", "skill-3"],
                }
            ],
        },
        lineage=ExecutionLineage(
            operation_name="curriculum_generate",
            skill_name="curriculum_generate",
            skill_version="test",
            provider="test",
            model="test",
        ),
        trace=ExecutionTrace(
            request_id="req-curriculum",
            operation_name="curriculum_generate",
            allowed_tools=[],
            prompt_preview=PromptPreview(system_prompt="", user_prompt=""),
            request_envelope=engine_module.OperationEnvelope.model_validate(
                {
                    "input": {"requestMode": "source_entry"},
                    "app_context": {"product": "homeschool-v2", "surface": "onboarding"},
                }
            ),
        ),
        prompt_preview=PromptPreview(system_prompt="", user_prompt=""),
    )

    def fake_execute(self, operation_name: str, _envelope_data: dict):
        if operation_name == "source_interpret":
            return source_response
        if operation_name == "curriculum_generate":
            return curriculum_response
        raise AssertionError(f"Unexpected operation: {operation_name}")

    monkeypatch.setattr(engine_module.AgentEngine, "execute", fake_execute, raising=True)

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

    assert result.operation_name == "curriculum_generate"
    assert result.artifact["units"][0]["skillIds"][0] == "skill-1"
    assert result.trace.agent_trace["orchestration_profile"] == "generate_from_source"
    assert [step["operation_name"] for step in result.trace.agent_trace["substeps"]] == [
        "source_interpret",
        "curriculum_generate",
    ]
