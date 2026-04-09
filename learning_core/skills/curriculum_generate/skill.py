from __future__ import annotations

from learning_core.contracts.curriculum import CurriculumArtifact, CurriculumGenerationRequest
from learning_core.contracts.progression import ProgressionGenerationRequest
from learning_core.runtime.context import RuntimeContext
from learning_core.runtime.policy import ExecutionPolicy
from learning_core.runtime.skill import SkillExecutionResult
from learning_core.skills.base import StructuredOutputSkill
from learning_core.skills.curriculum_common import build_skill_catalog_from_document
from learning_core.skills.progression_generate.skill import ProgressionGenerateSkill
from learning_core.skills.prompt_utils import append_user_authored_context, format_curriculum_transcript


class CurriculumGenerateSkill(StructuredOutputSkill):
    name = "curriculum_generate"
    input_model = CurriculumGenerationRequest
    output_model = CurriculumArtifact
    policy = ExecutionPolicy(
        skill_name="curriculum_generate",
        skill_version="2026-04-09",
        max_tokens=12000,
    )

    def build_user_prompt(self, payload: CurriculumGenerationRequest, context) -> str:
        lines = [
            f"Active learner: {payload.learnerName}",
            "",
            "Current requirement hints:",
            payload.requirementHints.model_dump_json(indent=2) if payload.requirementHints else "{}",
            "",
            "Pacing expectations inferred from the conversation:",
            payload.pacingExpectations.model_dump_json(indent=2) if payload.pacingExpectations else "{}",
        ]

        if payload.granularityGuidance:
            lines.extend(
                [
                    "",
                    "Granularity guidance:",
                    *[f"{index + 1}. {note}" for index, note in enumerate(payload.granularityGuidance)],
                ]
            )

        lines.extend(
            [
                "",
                "Conversation transcript:",
                format_curriculum_transcript(payload.messages),
            ]
        )

        if payload.correctionNotes:
            lines.extend(
                [
                    "",
                    "Correction notes for this retry:",
                    *[f"{index + 1}. {note}" for index, note in enumerate(payload.correctionNotes)],
                ]
            )

        append_user_authored_context(lines, context)
        lines.extend(["", "Generate the core curriculum artifact."])
        return "\n".join(lines)

    def execute(self, engine, payload: CurriculumGenerationRequest, context: RuntimeContext) -> SkillExecutionResult[CurriculumArtifact]:
        artifact, lineage, trace = engine.run_structured_output(
            skill=self,
            payload=payload,
            context=context,
        )
        skill_catalog = build_skill_catalog_from_document(artifact.document)
        if skill_catalog:
            progression_skill = ProgressionGenerateSkill()
            progression_payload = ProgressionGenerationRequest(
                learnerName=payload.learnerName,
                sourceTitle=artifact.source.title,
                sourceSummary=artifact.source.summary,
                skillCatalog=skill_catalog,
            )
            progression_context = RuntimeContext.create(
                operation_name="progression_generate",
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
            artifact = artifact.model_copy(update={"progression": progression_artifact})

        return SkillExecutionResult(
            artifact=artifact,
            lineage=lineage,
            trace=trace,
        )
