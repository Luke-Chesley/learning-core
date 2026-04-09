from __future__ import annotations

from learning_core.contracts import (
    ActivityArtifact,
    ActivityGenerationInput,
    CurriculumArtifact,
    CurriculumGenerationRequest,
    CurriculumRevisionRequest,
    CurriculumUpdateProposalArtifact,
    CurriculumUpdateProposalRequest,
    EvaluationArtifact,
    ProgressionArtifact,
    ProgressionGenerationRequest,
    ProgressionRevisionRequest,
    SessionEvaluationRequest,
    SessionPlanArtifact,
    SessionPlanGenerationRequest,
)
from learning_core.runtime.registry import SkillRegistry
from learning_core.skills.activity_generate.skill import ActivityGenerateSkill
from learning_core.skills.stub import StubSkillConfig, UnimplementedSkill


def build_skill_registry() -> SkillRegistry:
    registry = SkillRegistry()
    registry.register(
        "generate-activities-from-plan-session",
        ActivityGenerateSkill(),
    )

    registry.register(
        "generate-curriculum-from-scratch",
        UnimplementedSkill(
            StubSkillConfig(
                name="curriculum_generate",
                operation_name="generate-curriculum-from-scratch",
                skill_version="2026-04-08",
                input_model=CurriculumGenerationRequest,
                output_model=CurriculumArtifact,
            )
        ),
    )
    registry.register(
        "revise-existing-curriculum",
        UnimplementedSkill(
            StubSkillConfig(
                name="curriculum_revise",
                operation_name="revise-existing-curriculum",
                skill_version="2026-04-08",
                input_model=CurriculumRevisionRequest,
                output_model=CurriculumArtifact,
            )
        ),
    )
    registry.register(
        "generate-progression-model",
        UnimplementedSkill(
            StubSkillConfig(
                name="progression_generate",
                operation_name="generate-progression-model",
                skill_version="2026-04-08",
                input_model=ProgressionGenerationRequest,
                output_model=ProgressionArtifact,
            )
        ),
    )
    registry.register(
        "revise-progression-model",
        UnimplementedSkill(
            StubSkillConfig(
                name="progression_revise",
                operation_name="revise-progression-model",
                skill_version="2026-04-08",
                input_model=ProgressionRevisionRequest,
                output_model=ProgressionArtifact,
            )
        ),
    )
    registry.register(
        "generate-daily-session-plan",
        UnimplementedSkill(
            StubSkillConfig(
                name="session_generate",
                operation_name="generate-daily-session-plan",
                skill_version="2026-04-08",
                input_model=SessionPlanGenerationRequest,
                output_model=SessionPlanArtifact,
            )
        ),
    )
    registry.register(
        "evaluate-completed-session",
        UnimplementedSkill(
            StubSkillConfig(
                name="session_evaluate",
                operation_name="evaluate-completed-session",
                skill_version="2026-04-08",
                input_model=SessionEvaluationRequest,
                output_model=EvaluationArtifact,
            )
        ),
    )
    registry.register(
        "propose-curriculum-progression-updates",
        UnimplementedSkill(
            StubSkillConfig(
                name="curriculum_update_propose",
                operation_name="propose-curriculum-progression-updates",
                skill_version="2026-04-08",
                input_model=CurriculumUpdateProposalRequest,
                output_model=CurriculumUpdateProposalArtifact,
            )
        ),
    )
    return registry
