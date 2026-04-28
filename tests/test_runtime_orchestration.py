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
            "curriculumScale": "week",
            "planningModel": "session_sequence",
            "skills": [
                {
                    "skillId": "skill-1",
                    "domainTitle": "Math",
                    "strandTitle": "Pages 1-12",
                    "goalGroupTitle": "Workbook launch",
                    "title": "Warm-up from page 1",
                    "description": "Use the first page to orient to the workbook routine.",
                    "contentAnchorIds": ["anchor-1"],
                    "practiceCue": "Complete the first warm-up example.",
                    "assessmentCue": "Learner can explain the page-one example.",
                },
                {
                    "skillId": "skill-2",
                    "domainTitle": "Math",
                    "strandTitle": "Pages 1-12",
                    "goalGroupTitle": "Workbook launch",
                    "title": "Guided practice from pages 2-6",
                    "description": "Work the guided examples on pages 2 through 6.",
                    "contentAnchorIds": ["anchor-2"],
                    "practiceCue": "Solve one guided example together.",
                    "assessmentCue": "Learner follows the model with support.",
                },
                {
                    "skillId": "skill-3",
                    "domainTitle": "Math",
                    "strandTitle": "Pages 1-12",
                    "goalGroupTitle": "Workbook launch",
                    "title": "Independent practice from pages 7-12",
                    "description": "Try the independent practice from pages 7 through 12.",
                    "contentAnchorIds": ["anchor-3"],
                    "practiceCue": "Complete one independent problem.",
                    "assessmentCue": "Learner completes the problem and checks the answer.",
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
            "contentAnchors": [
                {"anchorId": "anchor-1", "title": "Page 1 warm-up", "summary": "The first page introduces the workbook routine.", "details": [], "sourceRefs": [{"label": "pages 1-12"}], "grounding": "source_grounded"},
                {"anchorId": "anchor-2", "title": "Pages 2-6 guided practice", "summary": "Pages 2 through 6 provide supported examples.", "details": [], "sourceRefs": [{"label": "pages 1-12"}], "grounding": "source_grounded"},
                {"anchorId": "anchor-3", "title": "Pages 7-12 independent practice", "summary": "Pages 7 through 12 provide independent practice.", "details": [], "sourceRefs": [{"label": "pages 1-12"}], "grounding": "source_grounded"},
            ],
            "teachableItems": [
                {"itemId": "item-1", "unitRef": "unit:1:pages-1-12", "title": "Workbook warm-up", "focusQuestion": "How does the first example work?", "contentAnchorIds": ["anchor-1"], "namedAnchors": ["page 1"], "vocabulary": [], "learnerOutcome": "Learner explains the first example.", "assessmentCue": "Learner can repeat the routine.", "misconceptions": [], "parentNotes": [], "skillIds": ["skill-1"], "estimatedSessions": 1, "sourceRefs": [{"label": "pages 1-12"}]},
                {"itemId": "item-2", "unitRef": "unit:1:pages-1-12", "title": "Guided workbook examples", "focusQuestion": "What does the model show?", "contentAnchorIds": ["anchor-2"], "namedAnchors": ["pages 2-6"], "vocabulary": [], "learnerOutcome": "Learner solves one guided example.", "assessmentCue": "Learner follows the model.", "misconceptions": [], "parentNotes": [], "skillIds": ["skill-2"], "estimatedSessions": 1, "sourceRefs": [{"label": "pages 1-12"}]},
                {"itemId": "item-3", "unitRef": "unit:1:pages-1-12", "title": "Independent workbook practice", "focusQuestion": "Can the learner try the routine alone?", "contentAnchorIds": ["anchor-3"], "namedAnchors": ["pages 7-12"], "vocabulary": [], "learnerOutcome": "Learner completes one independent problem.", "assessmentCue": "Learner checks the answer.", "misconceptions": [], "parentNotes": [], "skillIds": ["skill-3"], "estimatedSessions": 1, "sourceRefs": [{"label": "pages 1-12"}]},
            ],
            "deliverySequence": [
                {"sequenceId": "session-1", "position": 1, "label": "Session 1", "title": "Warm-up from page 1", "sessionFocus": "Use page 1 to learn the workbook routine.", "teachableItemId": "item-1", "contentAnchorIds": ["anchor-1"], "skillIds": ["skill-1"], "estimatedMinutes": 30, "evidenceToSave": [], "reviewOf": []},
                {"sequenceId": "session-2", "position": 2, "label": "Session 2", "title": "Guided practice from pages 2-6", "sessionFocus": "Work guided examples from pages 2 through 6.", "teachableItemId": "item-2", "contentAnchorIds": ["anchor-2"], "skillIds": ["skill-2"], "estimatedMinutes": 30, "evidenceToSave": [], "reviewOf": []},
                {"sequenceId": "session-3", "position": 3, "label": "Session 3", "title": "Independent practice from pages 7-12", "sessionFocus": "Try independent practice from pages 7 through 12.", "teachableItemId": "item-3", "contentAnchorIds": ["anchor-3"], "skillIds": ["skill-3"], "estimatedMinutes": 30, "evidenceToSave": [], "reviewOf": []},
            ],
            "sourceCoverage": [],
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
