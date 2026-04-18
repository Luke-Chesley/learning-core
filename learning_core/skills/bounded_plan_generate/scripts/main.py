from __future__ import annotations

import json

from learning_core.contracts.bounded_plan import (
    BoundedPlanArtifact,
    BoundedPlanGenerationRequest,
)
from learning_core.runtime.policy import ExecutionPolicy
from learning_core.skills.base import StructuredOutputSkill
from learning_core.skills.prompt_utils import (
    append_user_authored_context,
    build_openai_file_blocks,
    format_source_files,
)


class BoundedPlanGenerateSkill(StructuredOutputSkill):
    name = "bounded_plan_generate"
    input_model = BoundedPlanGenerationRequest
    output_model = BoundedPlanArtifact
    policy = ExecutionPolicy(
        skill_name="bounded_plan_generate",
        skill_version="2026-04-17",
        max_tokens=5000,
    )

    def build_user_prompt(self, payload: BoundedPlanGenerationRequest, context) -> str:
        lines = [
            f"Learner: {payload.learnerName}",
            f"Requested route: {payload.requestedRoute}",
            f"Routed route: {payload.routedRoute}",
            f"Source kind: {payload.sourceKind}",
            f"Source scale: {payload.sourceScale or 'None provided'}",
            f"Slice strategy: {payload.sliceStrategy or 'None provided'}",
            f"Chosen horizon: {payload.chosenHorizon}",
            f"Title candidate: {payload.titleCandidate or 'None provided'}",
            "",
            "Source packages:",
            json.dumps([source.model_dump(mode="json") for source in payload.sourcePackages], indent=2),
            "",
            "Attached source files:",
            format_source_files(payload.sourceFiles),
            "",
            "Slice notes:",
            json.dumps(payload.sliceNotes, indent=2),
            "",
            "Detected chunks:",
            json.dumps(payload.detectedChunks, indent=2),
            "",
            "Assumptions:",
            json.dumps(payload.assumptions, indent=2),
            "",
            "Source text:",
            payload.sourceText,
        ]
        append_user_authored_context(lines, context)
        lines.extend(
            [
                "",
                "Generate the smallest durable planning object that fits this source and horizon.",
                "The first lesson or day must be immediately teachable and ready to open as day 1.",
                "If attached source files are present, treat them as the primary source and use the text fields as supporting context.",
                "If the source is large, generate only the bounded initial slice implied by the source kind, source scale, and slice guidance.",
                "Do not generate fake long-range curriculum scope.",
                "Return all required fields from the bounded plan contract.",
                "The `document` field is required.",
                "Set `document` to a nested mapping of subject -> unit title -> ordered lesson title list.",
                "Every unit in `units` must also appear in `document`.",
                "Example `document` shape:",
                json.dumps(
                    {
                        "Math": {
                            "Current week fractions and decimals": [
                                "Fractions practice",
                                "Decimal review",
                                "Percent game",
                            ]
                        }
                    },
                    indent=2,
                ),
                "Return only valid JSON.",
            ]
        )
        return "\n".join(lines)

    def build_user_message_content(
        self,
        payload: BoundedPlanGenerationRequest,
        context,
        *,
        prompt_text: str | None = None,
        provider: str | None = None,
    ) -> str | list[dict]:
        prompt = prompt_text if prompt_text is not None else self.build_user_prompt(payload, context)
        if provider != "openai" or not payload.sourceFiles:
            return prompt
        return [{"type": "text", "text": prompt}, *build_openai_file_blocks(payload.sourceFiles)]
