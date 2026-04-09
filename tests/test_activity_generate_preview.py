from learning_core.contracts.activity import ActivityGenerationInput
from learning_core.contracts.operation import AppContext, PresentationContext, UserAuthoredContext
from learning_core.runtime.context import RuntimeContext
from learning_core.skills.activity_generate.scripts.main import ActivityGenerateSkill


def test_activity_generate_preview_includes_lesson_title():
    payload = ActivityGenerationInput.model_validate(
        {
            "learner_name": "Alex",
            "workflow_mode": "family_guided",
            "subject": "Math",
            "linked_skill_titles": ["Long Division"],
            "lesson_draft": {
                "schema_version": "1.0",
                "title": "Long Division",
                "lesson_focus": "Learn the long division algorithm.",
                "primary_objectives": ["Divide with support"],
                "success_criteria": ["Finish three problems"],
                "total_minutes": 35,
                "blocks": [
                    {
                        "type": "model",
                        "title": "Model it",
                        "minutes": 10,
                        "purpose": "Show the method",
                        "teacher_action": "Demonstrate on whiteboard",
                        "learner_action": "Take notes",
                        "materials_needed": [],
                        "optional": False,
                    }
                ],
                "materials": ["Workbook"],
                "teacher_notes": ["Use D-M-S-B language"],
                "adaptations": [],
                "assessment_artifact": "Workbook page",
            },
        }
    )

    preview = ActivityGenerateSkill().build_prompt_preview(
        payload,
        RuntimeContext.create(
            operation_name="activity_generate",
            app_context=AppContext(product="homeschool-v2", surface="today_workspace"),
            presentation_context=PresentationContext(),
            user_authored_context=UserAuthoredContext(),
        ),
    )

    assert "Long Division" in preview.user_prompt
    assert "ActivitySpec" in preview.system_prompt
