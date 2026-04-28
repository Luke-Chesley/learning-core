from __future__ import annotations

import json

from learning_core.contracts.curriculum import CurriculumArtifact, CurriculumGenerationRequest
from learning_core.observability.traces import PromptPreview
from learning_core.runtime.policy import ExecutionPolicy
from learning_core.skills.base import StructuredOutputSkill
from learning_core.skills.prompt_utils import (
    append_user_authored_context,
    build_openai_file_blocks,
    format_curriculum_transcript,
    format_source_files,
)


class CurriculumGenerateSkill(StructuredOutputSkill):
    name = "curriculum_generate"
    input_model = CurriculumGenerationRequest
    output_model = CurriculumArtifact
    policy = ExecutionPolicy(
        skill_name="curriculum_generate",
        skill_version="2026-04-19",
        max_tokens=12000,
    )

    def _scale_guidance(self, payload: CurriculumGenerationRequest) -> str:
        if payload.requestMode == "source_entry":
            planning_constraints = payload.planningConstraints
            total_sessions = planning_constraints.totalSessions if planning_constraints else None
            if total_sessions is not None:
                return (
                    f"Use planningModel session_sequence. planningConstraints.totalSessions is {total_sessions}; "
                    "pacing.totalSessions and deliverySequence must preserve that number exactly. Create one concrete "
                    "deliverySequence item, teachable item, and primary skill per session."
                )
            if payload.sourceKind == "curriculum_request":
                return (
                    "This is a parent-authored curriculum request. Build a concrete model-suggested curriculum map "
                    "from the stated topic, grade, learner context, and planningConstraints. Use session_sequence "
                    "when a total session count is present; otherwise choose the smallest honest planning model."
                )
            if payload.sourceKind == "timeboxed_plan":
                return (
                    "Use planningModel session_sequence. Preserve the requested session count; "
                    "deliverySequence must contain one concrete item per session. Use curriculumScale module "
                    "unless the timebox is only a single day or week."
                )
            if payload.sourceKind == "bounded_material":
                return (
                    "Keep the curriculum bounded, but choose planningModel single_lesson, content_map, "
                    "or session_sequence based on the source shape. Include concrete teachableItems and contentAnchors."
                )
            if payload.sourceKind == "comprehensive_source":
                return (
                    "Prefer curriculumScale reference_source or course with planningModel reference_map or source_sequence. "
                    "Represent the broader source with concrete content anchors rather than a shallow starter slice."
                )
            if payload.sourceKind == "structured_sequence":
                return (
                    "Use planningModel source_sequence unless an explicit session count calls for session_sequence. "
                    "Preserve the source order with concrete teachableItems."
                )
            if payload.recommendedHorizon in {"single_day", "few_days", "one_week"}:
                return (
                    "Prefer the smallest honest scale, but still include a teachable content map. "
                    "A compact curriculum does not need course-shaped hierarchy."
                )
            return (
                "Choose the smallest honest curriculumScale that still preserves the durable curriculum scope, "
                "and include concrete contentAnchors, teachableItems, and deliverySequence when the source is sequenced."
            )

        expectations = payload.pacingExpectations
        if expectations and expectations.totalWeeks is not None and expectations.totalWeeks <= 1:
            return "Prefer curriculumScale week and keep the structure compact; one unit can be enough, but it still needs concrete teachableItems."
        if expectations and expectations.totalSessionsUpperBound is not None and expectations.totalSessionsUpperBound <= 5:
            return "Prefer curriculumScale micro or week; avoid fake course hierarchy, but include concrete session/content detail."
        return "Choose the smallest honest curriculumScale from the conversation, from micro/week through module/course, and make the content map concrete."

    def build_user_prompt(self, payload: CurriculumGenerationRequest, context) -> str:
        lines = [
            f"Active learner: {payload.learnerName}",
            f"Request mode: {payload.requestMode}",
            f"Title candidate: {payload.titleCandidate or 'None provided'}",
            f"Scale guidance: {self._scale_guidance(payload)}",
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
                    "Planning constraints:",
                    payload.planningConstraints.model_dump_json(indent=2)
                    if payload.planningConstraints
                    else "{}",
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
                    json.dumps(payload.sourcePackages, indent=2, default=lambda value: getattr(value, "model_dump", lambda: str(value))()),
                    "",
                    "Attached source files:",
                    format_source_files(payload.sourceFiles or []),
                    "",
                    "Primary source text:",
                    payload.sourceText or "",
                ]
            )
        else:
            lines.extend(
                [
                    "",
                    "Current requirement hints:",
                    json.dumps(payload.requirementHints or {}, indent=2),
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
                "Return the durable curriculum artifact only.",
            ]
        )
        return "\n".join(lines)

    def build_validation_retry_preview(
        self,
        *,
        payload: CurriculumGenerationRequest,
        context,
        raw_artifact,
        error,
    ) -> PromptPreview:
        raw_json = json.dumps(raw_artifact, indent=2, default=str)
        return PromptPreview(
            system_prompt=self.read_skill_markdown(),
            user_prompt="\n".join(
                [
                    self.build_user_prompt(payload, context),
                    "",
                    "The previous JSON did not validate against the curriculum artifact contract.",
                    "Return one corrected JSON object only. Preserve the intended curriculum content while fixing schema violations.",
                    "",
                    "Validation error:",
                    str(error),
                    "",
                    "Correction rules:",
                    "- `source.rationale` must be an array of strings, never one string.",
                    "- `curriculumScale`, when present, must be one of micro, week, module, course, or reference_source.",
                    "- `planningModel` must be one of content_map, session_sequence, source_sequence, single_lesson, or reference_map.",
                    "- `skills[].domainTitle`, `skills[].strandTitle`, and `skills[].goalGroupTitle` are optional; do not invent fake hierarchy just to satisfy a course-shaped template.",
                    "- Every skill must be grounded by `contentAnchorIds` or by a `teachableItems[].skillIds` reference.",
                    "- Every unit must include `skillIds` that match existing top-level `skills[].skillId` values.",
                    "- Every `teachableItems[].unitRef` must match an existing unit.",
                    "- Every `teachableItems[].skillIds` value must match an existing skill.",
                    "- Every `teachableItems[].contentAnchorIds` value must match an existing content anchor.",
                    "- If planningModel is session_sequence and totalSessions is present, deliverySequence must contain exactly one item per session.",
                    "- Delivery sequence positions must be contiguous and start at 1.",
                    "- `estimatedWeeks`, `estimatedSessions`, `totalWeeks`, `sessionsPerWeek`, `sessionMinutes`, and `totalSessions` must be positive integers when present.",
                    "- Do not use `0` for any estimate. Use `1` for a very small unit or omit the estimate.",
                    "- Do not add `document`, `skillRefs`, `lessons`, `launchPlan`, or `progression`.",
                    "",
                    "Previous invalid JSON:",
                    raw_json,
                ]
            ),
        )

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
