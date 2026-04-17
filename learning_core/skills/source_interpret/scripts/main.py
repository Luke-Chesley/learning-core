from __future__ import annotations

import json

from learning_core.contracts.source_interpret import (
    SourceInterpretationHorizon,
    SourceInterpretationArtifact,
    SourceInterpretationRequest,
)
from learning_core.observability.traces import PromptPreview
from learning_core.runtime.policy import ExecutionPolicy
from learning_core.skills.base import StructuredOutputSkill
from learning_core.skills.prompt_utils import (
    append_user_authored_context,
    build_openai_file_blocks,
    format_source_files,
)


_RECOMMENDED_HORIZON_BY_SOURCE_KIND: dict[str, SourceInterpretationHorizon] = {
    "single_day_material": "today",
    "weekly_assignments": "current_week",
    "sequence_outline": "next_few_days",
    "topic_seed": "starter_module",
    "manual_shell": "starter_week",
    "ambiguous": "today",
}


class SourceInterpretSkill(StructuredOutputSkill):
    name = "source_interpret"
    input_model = SourceInterpretationRequest
    output_model = SourceInterpretationArtifact
    policy = ExecutionPolicy(
        skill_name="source_interpret",
        skill_version="2026-04-17",
        max_tokens=2500,
    )

    def build_user_prompt(self, payload: SourceInterpretationRequest, context) -> str:
        lines = [
            f"Requested route: {payload.requestedRoute}",
            f"User horizon intent: {payload.userHorizonIntent}",
            f"Input modalities: {', '.join(payload.inputModalities) if payload.inputModalities else 'none'}",
            f"Asset refs: {len(payload.assetRefs)}",
            f"Title candidate: {payload.titleCandidate or 'None provided'}",
            f"Learner: {payload.learnerName or 'Unknown learner'}",
            "",
            "Source packages:",
            json.dumps([source.model_dump(mode="json") for source in payload.sourcePackages], indent=2),
            "",
            "Attached source files:",
            format_source_files(payload.sourceFiles),
            "",
            "Extracted structure:",
            json.dumps(payload.extractedStructure or {}, indent=2),
            "",
            "Raw text:",
            payload.rawText or "None provided.",
            "",
            "Extracted text:",
            payload.extractedText,
        ]
        append_user_authored_context(lines, context)
        lines.extend(
            [
                "",
                "Interpret the source only.",
                "Do not generate curriculum, lesson steps, activities, or pacing beyond the recommended bounded horizon.",
                "Return only valid JSON.",
            ]
        )
        return "\n".join(lines)

    def build_user_message_content(
        self,
        payload: SourceInterpretationRequest,
        context,
        *,
        prompt_text: str | None = None,
        provider: str | None = None,
    ) -> str | list[dict]:
        prompt = prompt_text if prompt_text is not None else self.build_user_prompt(payload, context)
        if provider != "openai" or not payload.sourceFiles:
            return prompt
        return [{"type": "text", "text": prompt}, *build_openai_file_blocks(payload.sourceFiles)]

    def repair_invalid_artifact(self, *, raw_artifact, payload, context, error):
        if not isinstance(raw_artifact, dict):
            return None

        repaired = dict(raw_artifact)
        source_kind = repaired.get("sourceKind")
        if (
            repaired.get("recommendedHorizon") is None
            and isinstance(source_kind, str)
            and source_kind in _RECOMMENDED_HORIZON_BY_SOURCE_KIND
        ):
            repaired["recommendedHorizon"] = self._infer_recommended_horizon(
                payload,
                source_kind,
            )

        if repaired.get("needsConfirmation") is None and repaired.get("followUpQuestion"):
            repaired["needsConfirmation"] = True

        if repaired.get("assumptions") is None:
            repaired["assumptions"] = []
        if repaired.get("detectedChunks") is None:
            repaired["detectedChunks"] = []

        return repaired if repaired != raw_artifact else None

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
                "- Every response must include all required keys.",
                "- `recommendedHorizon` is required and may never be omitted.",
                "- If the source is weak or ambiguous, choose a conservative horizon instead of omitting the field.",
                '- Invalid example: {"sourceKind":"topic_seed","suggestedTitle":"Chess","confidence":"high"}',
                '- Valid example: {"sourceKind":"topic_seed","suggestedTitle":"Chess","confidence":"high","recommendedHorizon":"starter_module","assumptions":[],"detectedChunks":[],"followUpQuestion":null,"needsConfirmation":false}',
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

    def _infer_recommended_horizon(
        self,
        payload: SourceInterpretationRequest,
        source_kind: str,
    ) -> SourceInterpretationHorizon:
        if payload.userHorizonIntent == "today_only":
            return "today"
        return _RECOMMENDED_HORIZON_BY_SOURCE_KIND[source_kind]
