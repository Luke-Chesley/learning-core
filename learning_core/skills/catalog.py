from __future__ import annotations

from learning_core.runtime.registry import SkillRegistry
from learning_core.skills.activity_generate.skill import ActivityGenerateSkill
from learning_core.skills.copilot_chat.skill import CopilotChatSkill
from learning_core.skills.curriculum_generate.skill import CurriculumGenerateSkill
from learning_core.skills.curriculum_intake.skill import CurriculumIntakeSkill
from learning_core.skills.curriculum_revise.skill import CurriculumReviseSkill
from learning_core.skills.curriculum_update_propose.skill import CurriculumUpdateProposeSkill
from learning_core.skills.progression_generate.skill import ProgressionGenerateSkill
from learning_core.skills.progression_revise.skill import ProgressionReviseSkill
from learning_core.skills.session_evaluate.skill import SessionEvaluateSkill
from learning_core.skills.session_generate.skill import SessionGenerateSkill


def build_skill_registry() -> SkillRegistry:
    registry = SkillRegistry()
    registry.register(
        "activity_generate",
        ActivityGenerateSkill(),
    )
    registry.register(
        "session_generate",
        SessionGenerateSkill(),
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
