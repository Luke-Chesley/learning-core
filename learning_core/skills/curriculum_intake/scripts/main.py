from __future__ import annotations

import json

from learning_core.contracts.curriculum import CurriculumIntakeArtifact, CurriculumIntakeRequest
from learning_core.runtime.policy import ExecutionPolicy
from learning_core.skills.base import StructuredOutputSkill
from learning_core.skills.prompt_utils import append_user_authored_context, format_curriculum_transcript


class CurriculumIntakeSkill(StructuredOutputSkill):
    name = "curriculum_intake"
    input_model = CurriculumIntakeRequest
    output_model = CurriculumIntakeArtifact
    policy = ExecutionPolicy(
        skill_name="curriculum_intake",
        skill_version="2026-04-09",
        task_kind="chat",
        max_tokens=4096,
    )

    def build_user_prompt(self, payload: CurriculumIntakeRequest, context) -> str:
        lines = [
            f"Active learner: {payload.learnerName}",
            "",
            "Current requirement hints:",
            json.dumps(payload.requirementHints or {}, indent=2),
            "",
            "Conversation transcript:",
            format_curriculum_transcript(payload.messages),
        ]
        append_user_authored_context(lines, context)
        lines.extend(["", "Respond with the next assistant turn and the current intake state."])
        return "\n".join(lines)
