from __future__ import annotations

from learning_core.contracts.curriculum import CurriculumUpdateProposalArtifact, CurriculumUpdateProposalRequest
from learning_core.runtime.policy import ExecutionPolicy
from learning_core.skills.base import StructuredOutputSkill
from learning_core.skills.prompt_utils import append_user_authored_context


class CurriculumUpdateProposeSkill(StructuredOutputSkill):
    name = "curriculum_update_propose"
    input_model = CurriculumUpdateProposalRequest
    output_model = CurriculumUpdateProposalArtifact
    policy = ExecutionPolicy(
        skill_name="curriculum_update_propose",
        skill_version="2026-04-09",
        max_tokens=4000,
    )

    def build_user_prompt(self, payload: CurriculumUpdateProposalRequest, context) -> str:
        lines = [
            f"Evaluation summary: {payload.evaluationSummary}",
            f"Curriculum title: {payload.curriculumTitle or 'Unknown'}",
            f"Progression title: {payload.progressionTitle or 'Unknown'}",
        ]
        if payload.constraints:
            lines.extend(["", "Constraints:", *[f"- {item}" for item in payload.constraints]])
        append_user_authored_context(lines, context)
        lines.extend(["", "Propose concrete curriculum or progression updates."])
        return "\n".join(lines)
