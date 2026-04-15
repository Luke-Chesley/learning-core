from __future__ import annotations

import json

from learning_core.contracts.source_interpret import (
    SourceInterpretationArtifact,
    SourceInterpretationRequest,
)
from learning_core.runtime.policy import ExecutionPolicy
from learning_core.skills.base import StructuredOutputSkill
from learning_core.skills.prompt_utils import append_user_authored_context


class SourceInterpretSkill(StructuredOutputSkill):
    name = "source_interpret"
    input_model = SourceInterpretationRequest
    output_model = SourceInterpretationArtifact
    policy = ExecutionPolicy(
        skill_name="source_interpret",
        skill_version="2026-04-14",
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
