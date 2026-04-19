from __future__ import annotations

from learning_core.contracts.curriculum import CurriculumRevisionRequest, CurriculumRevisionTurn
from learning_core.runtime.policy import ExecutionPolicy
from learning_core.runtime.skill import SkillExecutionResult
from learning_core.skills.base import StructuredOutputSkill
from learning_core.skills.prompt_utils import append_user_authored_context, format_curriculum_transcript


class CurriculumReviseSkill(StructuredOutputSkill):
    name = "curriculum_revise"
    input_model = CurriculumRevisionRequest
    output_model = CurriculumRevisionTurn
    policy = ExecutionPolicy(
        skill_name="curriculum_revise",
        skill_version="2026-04-19",
        max_tokens=12000,
    )

    def build_user_prompt(self, payload: CurriculumRevisionRequest, context) -> str:
        lines = [
            f"Active learner: {payload.learnerName}",
            "",
            "Current curriculum snapshot:",
            payload.currentCurriculum and __import__("json").dumps(payload.currentCurriculum, indent=2) or "{}",
        ]

        if payload.currentRequest:
            lines.extend(["", "Latest parent request:", payload.currentRequest])

        lines.extend(
            [
                "",
                "Revision conversation transcript:",
                format_curriculum_transcript(payload.messages),
                "",
                "Revision instructions:",
                "- Read the snapshot and transcript directly.",
                "- Decide whether the change is a split, rename, targeted adjust, or broader rewrite.",
                "- Preserve unchanged branches unless the parent explicitly asked for a broader rewrite.",
                "- Keep the canonical tree shape: domain -> strand -> goal group -> skill.",
                "- Preserve teachable granularity while keeping the tree coherent.",
                "- Units should remain coarse curriculum groupings, not lesson plans.",
                "- Return the full revised curriculum artifact when action is \"apply\".",
                "- If the request is too vague to apply safely, ask one precise clarification question.",
            ]
        )

        if payload.correctionNotes:
            lines.extend(
                [
                    "",
                    "Retry correction notes:",
                    *[f"{index + 1}. {note}" for index, note in enumerate(payload.correctionNotes)],
                ]
            )

        append_user_authored_context(lines, context)
        lines.extend(["", "Respond with either one clarification question or the full revised curriculum artifact."])
        return "\n".join(lines)

    def execute(self, engine, payload: CurriculumRevisionRequest, context) -> SkillExecutionResult[CurriculumRevisionTurn]:
        turn, lineage, trace = engine.run_structured_output(
            skill=self,
            payload=payload,
            context=context,
        )
        return SkillExecutionResult(
            artifact=turn,
            lineage=lineage,
            trace=trace,
        )
