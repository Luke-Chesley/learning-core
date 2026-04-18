from __future__ import annotations

from learning_core.contracts.curriculum import CurriculumArtifact, CurriculumGenerationRequest
from learning_core.runtime.context import RuntimeContext
from learning_core.runtime.policy import ExecutionPolicy
from learning_core.runtime.skill import SkillExecutionResult
from learning_core.skills.base import StructuredOutputSkill
from learning_core.skills.curriculum_common import build_progression_request_from_artifact
from learning_core.skills.progression_generate.scripts.main import ProgressionGenerateSkill
from learning_core.skills.prompt_utils import (
    append_user_authored_context,
    build_openai_file_blocks,
    format_curriculum_transcript,
    format_source_files,
)


def _list_opening_lessons(artifact: CurriculumArtifact):
    opening_ref_set = set(artifact.launchPlan.openingLessonRefs)
    return [
        lesson
        for unit in artifact.units
        for lesson in unit.lessons
        if lesson.lessonRef in opening_ref_set
    ]


def _requires_task_first_retry(
    payload: CurriculumGenerationRequest,
    artifact: CurriculumArtifact,
) -> bool:
    if payload.requestMode != "source_entry" or payload.deliveryPattern != "task_first":
        return False
    opening_lessons = _list_opening_lessons(artifact)
    if not opening_lessons:
        return False
    return not any(lesson.lessonType == "task" for lesson in opening_lessons)


def _build_task_first_retry_notes(existing_notes: list[str] | None = None) -> list[str]:
    notes = list(existing_notes or [])
    notes.extend(
        [
            "This source is task_first. The opening arc must include a real source task within the first 1 to 3 lessons unless setup or safety truly blocks it.",
            "Keep setup, orientation, and rationale compressed into minimal support instead of the primary opener.",
            "Ensure launchPlan.openingLessonRefs includes at least one lessonType of task.",
        ]
    )
    return notes


class CurriculumGenerateSkill(StructuredOutputSkill):
    name = "curriculum_generate"
    input_model = CurriculumGenerationRequest
    output_model = CurriculumArtifact
    policy = ExecutionPolicy(
        skill_name="curriculum_generate",
        skill_version="2026-04-17",
        max_tokens=12000,
    )

    def build_user_prompt(self, payload: CurriculumGenerationRequest, context) -> str:
        lines = [
            f"Active learner: {payload.learnerName}",
            f"Request mode: {payload.requestMode}",
            f"Title candidate: {payload.titleCandidate or 'None provided'}",
        ]

        if payload.requestMode == "source_entry":
            lines.extend(
                [
                    f"Requested route: {payload.requestedRoute or 'None provided'}",
                    f"Routed route: {payload.routedRoute or 'None provided'}",
                    "",
                    f"Source kind: {payload.sourceKind}",
                    f"Entry strategy: {payload.entryStrategy}",
                    f"Entry label: {payload.entryLabel or 'None provided'}",
                    f"Continuation mode: {payload.continuationMode}",
                    f"Delivery pattern: {payload.deliveryPattern}",
                    f"Recommended horizon: {payload.recommendedHorizon}",
                    "",
                    "Assumptions:",
                    (payload.assumptions or []) and "\n".join(
                        f"- {value}" for value in (payload.assumptions or [])
                    )
                    or "- None provided",
                    "",
                    "Detected chunks:",
                    (payload.detectedChunks or []) and "\n".join(
                        f"- {value}" for value in (payload.detectedChunks or [])
                    )
                    or "- None provided",
                    "",
                    "Source packages:",
                    payload.model_dump_json(indent=2, include={"sourcePackages"}),
                    "",
                    "Attached source files:",
                    format_source_files(payload.sourceFiles or []),
                    "",
                    "Primary source text:",
                    payload.sourceText or "",
                ]
            )
            if payload.correctionNotes:
                lines.extend(
                    [
                        "",
                        "Correction notes for this retry:",
                        *[
                            f"{index + 1}. {note}"
                            for index, note in enumerate(payload.correctionNotes)
                        ],
                    ]
                )
        else:
            lines.extend(
                [
                    "",
                    "Current requirement hints:",
                    payload.requirementHints.model_dump_json(indent=2)
                    if payload.requirementHints
                    else "{}",
                    "",
                    "Pacing expectations inferred from the conversation:",
                    payload.pacingExpectations.model_dump_json(indent=2)
                    if payload.pacingExpectations
                    else "{}",
                ]
            )

            if payload.granularityGuidance:
                lines.extend(
                    [
                        "",
                        "Granularity guidance:",
                        *[
                            f"{index + 1}. {note}"
                            for index, note in enumerate(payload.granularityGuidance)
                        ],
                    ]
                )

            lines.extend(
                [
                    "",
                    "Conversation transcript:",
                    format_curriculum_transcript(payload.messages or []),
                ]
            )

            if payload.correctionNotes:
                lines.extend(
                    [
                        "",
                        "Correction notes for this retry:",
                        *[
                            f"{index + 1}. {note}"
                            for index, note in enumerate(payload.correctionNotes)
                        ],
                    ]
                )

        append_user_authored_context(lines, context)
        lines.extend(
            [
                "",
                "Return the durable curriculum artifact plus launchPlan.",
            ]
        )
        return "\n".join(lines)

    def build_user_message_content(
        self,
        payload: CurriculumGenerationRequest,
        context,
        *,
        prompt_text: str | None = None,
        provider: str | None = None,
    ) -> str | list[dict]:
        prompt = prompt_text if prompt_text is not None else self.build_user_prompt(payload, context)
        source_files = payload.sourceFiles or []
        if provider != "openai" or payload.requestMode != "source_entry" or not source_files:
            return prompt
        return [{"type": "text", "text": prompt}, *build_openai_file_blocks(source_files)]

    def execute(self, engine, payload: CurriculumGenerationRequest, context: RuntimeContext) -> SkillExecutionResult[CurriculumArtifact]:
        artifact, lineage, trace = engine.run_structured_output(
            skill=self,
            payload=payload,
            context=context,
        )
        if _requires_task_first_retry(payload, artifact):
            retry_payload = payload.model_copy(
                update={
                    "correctionNotes": _build_task_first_retry_notes(payload.correctionNotes),
                }
            )
            artifact, lineage, trace = engine.run_structured_output(
                skill=self,
                payload=retry_payload,
                context=context,
            )
            if _requires_task_first_retry(retry_payload, artifact):
                raise ValueError(
                    "task_first source_entry generation must include a task lesson in launchPlan.openingLessonRefs."
                )

        progression_payload = build_progression_request_from_artifact(
            artifact,
            learner_name=payload.learnerName,
            request_mode=payload.requestMode,
            source_kind=payload.sourceKind,
            delivery_pattern=payload.deliveryPattern,
            entry_strategy=payload.entryStrategy,
            continuation_mode=payload.continuationMode,
        )
        if progression_payload.skillCatalog:
            progression_skill = ProgressionGenerateSkill()
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
