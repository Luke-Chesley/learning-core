from __future__ import annotations

from learning_core.runtime.registry import SkillRegistry
from learning_core.skills.activity_feedback.scripts.main import ActivityFeedbackSkill
from learning_core.skills.activity_generate.scripts.main import ActivityGenerateSkill
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


def build_skill_registry() -> SkillRegistry:
    registry = SkillRegistry()
    registry.register(
        "activity_generate",
        ActivityGenerateSkill(),
    )
    registry.register(
        "activity_feedback",
        ActivityFeedbackSkill(),
    )
    registry.register(
        "widget_transition",
        WidgetTransitionSkill(),
    )
    registry.register(
        "session_generate",
        SessionGenerateSkill(),
    )
    registry.register(
        "source_interpret",
        SourceInterpretSkill(),
    )
    registry.register(
        "curriculum_intake",
        CurriculumIntakeSkill(),
    )
    registry.register(
        "copilot_chat",
        CopilotChatSkill(),
    )
    registry.register(
        "curriculum_generate",
        CurriculumGenerateSkill(),
    )
    registry.register(
        "curriculum_revise",
        CurriculumReviseSkill(),
    )
    registry.register(
        "progression_generate",
        ProgressionGenerateSkill(),
    )
    registry.register(
        "progression_revise",
        ProgressionReviseSkill(),
    )
    registry.register(
        "session_evaluate",
        SessionEvaluateSkill(),
    )
    registry.register(
        "curriculum_update_propose",
        CurriculumUpdateProposeSkill(),
    )

    return registry
