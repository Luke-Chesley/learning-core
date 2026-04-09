from __future__ import annotations

from learning_core.contracts.curriculum import CurriculumArtifact, CurriculumRevisionRequest, CurriculumRevisionTurn
from learning_core.contracts.progression import ProgressionRevisionRequest
from learning_core.runtime.context import RuntimeContext
from learning_core.runtime.policy import ExecutionPolicy
from learning_core.runtime.skill import SkillExecutionResult
from learning_core.skills.base import StructuredOutputSkill
from learning_core.skills.curriculum_common import build_skill_catalog_from_document
from learning_core.skills.progression_revise.skill import ProgressionReviseSkill
from learning_core.skills.prompt_utils import append_user_authored_context, format_curriculum_transcript


class CurriculumReviseSkill(StructuredOutputSkill):
    name = "curriculum_revise"
    input_model = CurriculumRevisionRequest
    output_model = CurriculumRevisionTurn
    policy = ExecutionPolicy(
        skill_name="curriculum_revise",
        skill_version="2026-04-09",
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
                "- For split requests, replace the target skill with sibling skills under the same parent.",
                "- Do not wrap the old skill as a new parent unless explicitly requested.",
                "- Do not invent a new goal group unless explicitly requested.",
                "- For rename requests, keep the structure the same and change wording only.",
                "- For targeted adjust requests, keep the change local unless a broader rewrite is requested.",
                "- Preserve teachable granularity while keeping the tree coherent and free of taxonomy noise.",
                "- If a branch is too broad for the learner or pacing, split it into sibling skills rather than compressing multiple procedures into one leaf.",
                "- Return the full revised artifact when action is \"apply\".",
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

    def execute(self, engine, payload: CurriculumRevisionRequest, context: RuntimeContext) -> SkillExecutionResult[CurriculumRevisionTurn]:
        turn, lineage, trace = engine.run_structured_output(
            skill=self,
            payload=payload,
            context=context,
        )
        artifact: CurriculumArtifact | None = turn.artifact
        if artifact is not None:
            skill_catalog = build_skill_catalog_from_document(artifact.document)
            if skill_catalog:
                progression_skill = ProgressionReviseSkill()
                progression_payload = ProgressionRevisionRequest(
                    learnerName=payload.learnerName,
                    sourceTitle=artifact.source.title,
                    sourceSummary=artifact.source.summary,
                    skillCatalog=skill_catalog,
                    revisionRequest=payload.currentRequest,
                )
                progression_context = RuntimeContext.create(
                    operation_name="progression_revise",
                    request_id=context.request_id,
                    app_context=context.app_context,
                    presentation_context=context.presentation_context,
                    user_authored_context=context.user_authored_context,
                )
                progression_artifact, _, _ = engine.run_structured_output(
                    skill=progression_skill,
                    payload=progression_payload,
                    context=progression_context,
                )
                updated_artifact = artifact.model_copy(update={"progression": progression_artifact})
                turn = turn.model_copy(update={"artifact": updated_artifact})

        return SkillExecutionResult(
            artifact=turn,
            lineage=lineage,
            trace=trace,
        )
