from __future__ import annotations

from typing import Any, Callable

from learning_core.observability.traces import PromptPreview
from learning_core.skills.activity_generate.scripts.main import ActivityGenerateSkill
from learning_core.skills.activity_feedback.scripts.main import ActivityFeedbackSkill
from learning_core.skills.bounded_plan_generate.scripts.main import BoundedPlanGenerateSkill
from learning_core.skills.copilot_chat.scripts.main import CopilotChatSkill
from learning_core.skills.curriculum_generate.scripts.main import CurriculumGenerateSkill
from learning_core.skills.curriculum_intake.scripts.main import CurriculumIntakeSkill
from learning_core.skills.curriculum_revise.scripts.main import CurriculumReviseSkill
from learning_core.skills.curriculum_update_propose.scripts.main import CurriculumUpdateProposeSkill
from learning_core.skills.progression_generate.scripts.main import ProgressionGenerateSkill
from learning_core.skills.progression_revise.scripts.main import ProgressionReviseSkill
from learning_core.skills.session_evaluate.scripts.main import SessionEvaluateSkill
from learning_core.skills.session_generate.scripts.main import SessionGenerateSkill
from learning_core.skills.source_interpret.scripts.main import SourceInterpretSkill
from learning_core.skills.widget_transition.scripts.main import WidgetTransitionSkill
from learning_core.workflow_cards.base import WorkflowCardDefinition


def _append_pack_prompt_sections(base_prompt: str, selected_packs: list[Any]) -> str:
    extra_sections = [
        section.strip()
        for pack in selected_packs
        for section in getattr(pack, "prompt_sections", ())
        if isinstance(section, str) and section.strip()
    ]
    if not extra_sections:
        return base_prompt
    return "\n\n".join([base_prompt, *extra_sections])


def _skill_prompt_preview_builder(skill_factory: Callable[[], Any], *, append_pack_sections: bool = True):
    def builder(payload: Any, context: Any, _runtime_request: Any, selected_packs: list[Any]) -> PromptPreview:
        skill = skill_factory()
        preview = skill.build_prompt_preview(payload, context)
        if not append_pack_sections:
            return preview
        return PromptPreview(
            system_prompt=preview.system_prompt,
            user_prompt=_append_pack_prompt_sections(preview.user_prompt, selected_packs),
        )

    return builder


WORKFLOW_CARD_REGISTRY: dict[str, WorkflowCardDefinition] = {
    "activity_evaluation": WorkflowCardDefinition(
        name="activity_evaluation",
        supported_task_profiles=("activity_evaluation",),
        supported_response_types=("activity_feedback", "evaluation"),
        prompt_preview_builder=_skill_prompt_preview_builder(ActivityFeedbackSkill, append_pack_sections=False),
    ),
    "activity_generation": WorkflowCardDefinition(
        name="activity_generation",
        supported_task_profiles=("adaptive_or_bounded_activity_generation",),
        supported_response_types=("activity_spec",),
        prompt_preview_builder=_skill_prompt_preview_builder(ActivityGenerateSkill, append_pack_sections=False),
        allowed_tool_families=("read_pack_docs", "read_context"),
        pack_categories=("domain", "subject", "interaction"),
    ),
    "artifact_revision": WorkflowCardDefinition(
        name="artifact_revision",
        supported_task_profiles=("artifact_revision",),
        supported_response_types=("curriculum_artifact_revision", "progression_artifact"),
        prompt_preview_builder=_skill_prompt_preview_builder(CurriculumReviseSkill),
        pack_categories=("domain",),
    ),
    "bounded_day_generation": WorkflowCardDefinition(
        name="bounded_day_generation",
        supported_task_profiles=("bounded_day_generation",),
        supported_response_types=("lesson_draft",),
        prompt_preview_builder=_skill_prompt_preview_builder(SessionGenerateSkill),
        pack_categories=("domain",),
    ),
    "curriculum_intake": WorkflowCardDefinition(
        name="curriculum_intake",
        supported_task_profiles=("intake_dialogue",),
        supported_response_types=("intake_turn",),
        prompt_preview_builder=_skill_prompt_preview_builder(CurriculumIntakeSkill),
        pack_categories=("domain",),
    ),
    "interactive_assistance": WorkflowCardDefinition(
        name="interactive_assistance",
        supported_task_profiles=("interactive_assistance",),
        supported_response_types=("summary", "widget_transition"),
        prompt_preview_builder=_skill_prompt_preview_builder(CopilotChatSkill),
    ),
    "long_horizon_planning": WorkflowCardDefinition(
        name="long_horizon_planning",
        supported_task_profiles=("long_horizon_planning",),
        supported_response_types=("curriculum_artifact", "progression_artifact"),
        prompt_preview_builder=_skill_prompt_preview_builder(CurriculumGenerateSkill),
        pack_categories=("domain",),
    ),
    "progression_generation": WorkflowCardDefinition(
        name="progression_generation",
        supported_task_profiles=("long_horizon_planning",),
        supported_response_types=("progression_artifact",),
        prompt_preview_builder=_skill_prompt_preview_builder(ProgressionGenerateSkill),
        pack_categories=("domain",),
    ),
    "proposal_generation": WorkflowCardDefinition(
        name="proposal_generation",
        supported_task_profiles=("proposal_generation",),
        supported_response_types=("proposal",),
        prompt_preview_builder=_skill_prompt_preview_builder(CurriculumUpdateProposeSkill),
        pack_categories=("domain",),
    ),
    "session_synthesis": WorkflowCardDefinition(
        name="session_synthesis",
        supported_task_profiles=("session_synthesis",),
        supported_response_types=("evaluation",),
        prompt_preview_builder=_skill_prompt_preview_builder(SessionEvaluateSkill),
        pack_categories=("domain",),
    ),
    "source_interpret": WorkflowCardDefinition(
        name="source_interpret",
        supported_task_profiles=("source_interpret",),
        supported_response_types=("source_interpretation",),
        prompt_preview_builder=_skill_prompt_preview_builder(SourceInterpretSkill),
        pack_categories=("domain",),
    ),
    "weekly_expansion": WorkflowCardDefinition(
        name="weekly_expansion",
        supported_task_profiles=("weekly_expansion",),
        supported_response_types=("bounded_plan",),
        prompt_preview_builder=_skill_prompt_preview_builder(BoundedPlanGenerateSkill),
        pack_categories=("domain",),
    ),
    "widget_transition": WorkflowCardDefinition(
        name="widget_transition",
        supported_task_profiles=("interactive_assistance",),
        supported_response_types=("widget_transition",),
        prompt_preview_builder=_skill_prompt_preview_builder(WidgetTransitionSkill, append_pack_sections=False),
    ),
    "progression_revision": WorkflowCardDefinition(
        name="progression_revision",
        supported_task_profiles=("artifact_revision",),
        supported_response_types=("progression_artifact",),
        prompt_preview_builder=_skill_prompt_preview_builder(ProgressionReviseSkill),
        pack_categories=("domain",),
    ),
}


def get_workflow_card(name: str) -> WorkflowCardDefinition:
    return WORKFLOW_CARD_REGISTRY[name]
