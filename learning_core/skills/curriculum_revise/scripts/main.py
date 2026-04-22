from __future__ import annotations

import json

from learning_core.observability.traces import PromptPreview
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
        skill_version="2026-04-22",
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

    def repair_invalid_artifact(self, *, raw_artifact, payload, context, error):
        del payload, context, error
        if not isinstance(raw_artifact, dict):
            return None

        repaired = dict(raw_artifact)
        artifact = repaired.get("artifact")
        if repaired.get("action") != "apply" or not isinstance(artifact, dict):
            return None

        expected_artifact_keys = {"source", "intakeSummary", "pacing", "document", "units"}
        document = artifact.get("document")
        if document is None:
            document = {}
        if not isinstance(document, dict):
            return None

        moved_any = False
        repaired_artifact = dict(artifact)
        repaired_document = dict(document)

        for key, value in list(repaired_artifact.items()):
            if key in expected_artifact_keys:
                continue
            if not isinstance(value, (dict, list, str)):
                continue
            if key in repaired_document:
                continue
            repaired_document[key] = value
            repaired_artifact.pop(key, None)
            moved_any = True

        if not moved_any:
            return None

        repaired_artifact["document"] = repaired_document
        repaired["artifact"] = repaired_artifact
        return repaired

    def build_validation_retry_preview(
        self,
        *,
        payload,
        context,
        raw_artifact,
        error,
    ) -> PromptPreview | None:
        system_prompt = "\n\n".join(
            [
                self.read_skill_markdown(),
                "Repair instructions:",
                "- The previous response was invalid.",
                "- Return only one corrected JSON object.",
                "- The top-level shape must be exactly assistantMessage, action, changeSummary, and optional artifact.",
                "- When action is apply, artifact may contain only source, intakeSummary, pacing, document, and units.",
                "- Every curriculum domain, strand, goal group, and skill title belongs inside artifact.document, never as extra keys beside document.",
                "- Keep the document tree in the canonical domain -> strand -> goal group -> skill shape.",
                "- Preserve the intended curriculum content while fixing the JSON structure.",
            ]
        )
        user_prompt = "\n".join(
            [
                self.build_user_prompt(payload, context),
                "",
                "Previous invalid JSON:",
                json.dumps(raw_artifact, indent=2, ensure_ascii=True),
                "",
                f"Validation error: {error}",
                "",
                "Repair the JSON so it matches the exact schema. Return only the corrected JSON object.",
            ]
        )
        return PromptPreview(system_prompt=system_prompt, user_prompt=user_prompt)
