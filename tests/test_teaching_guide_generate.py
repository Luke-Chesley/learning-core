from __future__ import annotations

import pytest

from learning_core.contracts.operation import AppContext, PresentationContext, UserAuthoredContext
from learning_core.contracts.teaching_guide import TeachingGuideArtifact, TeachingGuideGenerationRequest
from learning_core.response_types.registry import get_response_type
from learning_core.runtime.context import RuntimeContext
from learning_core.runtime.engine import AgentEngine
from learning_core.skills.catalog import build_skill_registry
from learning_core.skills.teaching_guide_generate.scripts.main import TeachingGuideGenerateSkill
from learning_core.workflow_cards.registry import get_workflow_card


def _context() -> RuntimeContext:
    return RuntimeContext.create(
        operation_name="teaching_guide_generate",
        request_id="test-teaching-guide",
        app_context=AppContext(product="homeschool-v2", surface="today"),
        presentation_context=PresentationContext(audience="parent"),
        user_authored_context=UserAuthoredContext(parent_goal="Keep this easy to teach before lunch."),
    )


def _request() -> TeachingGuideGenerationRequest:
    return TeachingGuideGenerationRequest.model_validate(
        {
            "lesson": {
                "title": "Equivalent fractions",
                "objective": "Recognize that 1/2 and 2/4 name the same amount.",
                "materials": ["paper strips"],
            },
            "source_context": {
                "sourceTitle": "Fractions Unit",
                "facts": ["Use fraction strips to compare equal parts."],
            },
            "route_items": [{"title": "Equivalent fractions", "objective": "Compare equal parts"}],
            "learner_context": {"age": 9},
            "teacher_context": {"subject_comfort": "medium"},
            "guidance_mode": "preteach",
        }
    )


def _artifact_payload(**overrides):
    payload = {
        "title": "Parent guide: Equivalent fractions",
        "audience": "parent",
        "guidance_mode": "preteach",
        "lesson_focus": "Help the learner see that two fraction names can describe the same amount.",
        "parent_brief": {
            "summary": "Use paper strips to compare halves and fourths.",
            "why_it_matters": "This prepares the learner to simplify and compare fractions.",
            "time_needed_minutes": 12,
            "materials": ["paper strips"],
        },
        "teach_it": {
            "setup": "Fold one strip into halves and another into fourths.",
            "steps": [
                "Show one half beside two fourths.",
                "Ask what amount each strip covers.",
                "Name both amounts as equal.",
            ],
            "vocabulary": [
                {
                    "term": "equivalent",
                    "parent_friendly_definition": "Different names for the same amount.",
                }
            ],
            "worked_example": "One half covers the same length as two fourths.",
        },
        "guided_questions": [
            {
                "question": "Which pieces cover the same space?",
                "listen_for": "The learner points to one half and two fourths.",
                "follow_up": "Ask them to explain how they know.",
            },
            {
                "question": "Can two names mean the same amount?",
                "listen_for": "The learner says yes and names both fractions.",
            },
        ],
        "common_misconceptions": [
            {
                "misconception": "A larger denominator always means a larger amount.",
                "why_it_happens": "The learner may focus on the number instead of piece size.",
                "repair_move": "Compare piece sizes with the same whole visible.",
                "easier_examples": ["one half and two fourths", "one third and two sixths", "one whole and two halves"],
            }
        ],
        "practice_plan": {
            "quick_warmup": "Name one half and two fourths.",
            "parent_moves": ["Keep the same whole visible.", "Ask the learner to match equal coverage."],
            "independent_try": "Have the learner draw another equivalent pair.",
        },
        "check_understanding": {
            "prompts": ["Show me two fractions that match."],
            "evidence_of_understanding": ["The learner explains equal coverage using the same whole."],
            "if_stuck": "Return to folding strips.",
            "if_ready": "Try thirds and sixths.",
        },
        "adaptation_moves": [
            {"signal": "The learner compares only numbers.", "move": "Point back to piece size and the whole."}
        ],
        "recordkeeping": [
            {
                "note": "Learner matched one half and two fourths with a drawing.",
                "evidence_to_save": "Photo of the strip model.",
            }
        ],
        "outsource_flags": [],
        "adult_review_required": False,
    }
    payload.update(overrides)
    return payload


def test_teaching_guide_request_requires_lesson_basis():
    with pytest.raises(ValueError, match="lesson or existing_session_artifact"):
        TeachingGuideGenerationRequest.model_validate({})


def test_teaching_guide_artifact_enforces_parent_audience_and_preteach_questions():
    with pytest.raises(ValueError):
        TeachingGuideArtifact.model_validate(_artifact_payload(audience="learner"))

    with pytest.raises(ValueError, match="guided_questions"):
        TeachingGuideArtifact.model_validate(_artifact_payload(guided_questions=[]))


def test_teaching_guide_artifact_requires_exactly_three_easier_examples():
    payload = _artifact_payload()
    payload["common_misconceptions"][0]["easier_examples"] = ["one half and two fourths", "one third and two sixths"]

    with pytest.raises(ValueError):
        TeachingGuideArtifact.model_validate(payload)


def test_teaching_guide_artifact_blocks_legal_and_diagnosis_claims():
    with pytest.raises(ValueError, match="legal guarantees"):
        TeachingGuideArtifact.model_validate(
            _artifact_payload(
                recordkeeping=[
                    {
                        "note": "This guarantees state law compliance.",
                        "evidence_to_save": "Worksheet",
                    }
                ]
            )
        )


def test_thin_source_can_require_adult_review_without_questions_or_misconceptions():
    artifact = TeachingGuideArtifact.model_validate(
        _artifact_payload(
            guided_questions=[],
            common_misconceptions=[],
            outsource_flags=["thin_source"],
            adult_review_required=True,
        )
    )

    assert artifact.adult_review_required is True


def test_teaching_guide_prompt_preview_mentions_guardrails_and_context():
    skill = TeachingGuideGenerateSkill()
    preview = skill.build_prompt_preview(_request(), _context())

    assert "Audience: parent" in preview.user_prompt
    assert "Equivalent fractions" in preview.user_prompt
    assert "Do not include legal compliance" in preview.user_prompt
    assert "Do not invent source facts" in preview.system_prompt


def test_teaching_guide_operation_is_registered_for_runtime_surfaces():
    registry = build_skill_registry()
    operation_names = {operation.operation_name for operation in registry.list_operations()}
    assert "teaching_guide_generate" in operation_names

    definition = get_response_type("teaching_guide_artifact")
    assert definition.artifact_model is TeachingGuideArtifact

    card = get_workflow_card("teaching_guide_generation")
    assert card.supported_task_profiles == ("teaching_support",)
    assert card.supported_response_types == ("teaching_guide_artifact",)


def test_teaching_guide_kernel_preview_exposes_runtime_metadata():
    engine = AgentEngine(build_skill_registry())

    preview = engine.preview(
        "teaching_guide_generate",
        {
            "input": _request().model_dump(mode="json"),
            "app_context": {
                "product": "homeschool-v2",
                "surface": "today",
            },
            "presentation_context": {
                "audience": "parent",
            },
        },
    )

    assert preview.task_profile == "teaching_support"
    assert preview.response_type == "teaching_guide_artifact"
    assert preview.workflow_card == "teaching_guide_generation"
