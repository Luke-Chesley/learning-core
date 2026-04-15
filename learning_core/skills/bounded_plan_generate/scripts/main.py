from __future__ import annotations

import json

from learning_core.contracts.bounded_plan import (
    BoundedPlanArtifact,
    BoundedPlanGenerationRequest,
)
from learning_core.runtime.policy import ExecutionPolicy
from learning_core.skills.base import StructuredOutputSkill
from learning_core.skills.prompt_utils import append_user_authored_context


class BoundedPlanGenerateSkill(StructuredOutputSkill):
    name = "bounded_plan_generate"
    input_model = BoundedPlanGenerationRequest
    output_model = BoundedPlanArtifact
    policy = ExecutionPolicy(
        skill_name="bounded_plan_generate",
        skill_version="2026-04-14",
        max_tokens=5000,
    )

    def build_user_prompt(self, payload: BoundedPlanGenerationRequest, context) -> str:
        lines = [
            f"Learner: {payload.learnerName}",
            f"Requested route: {payload.requestedRoute}",
            f"Routed route: {payload.routedRoute}",
            f"Source kind: {payload.sourceKind}",
            f"Chosen horizon: {payload.chosenHorizon}",
            f"Title candidate: {payload.titleCandidate or 'None provided'}",
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
                "Do not generate fake long-range curriculum scope.",
                "Return only valid JSON.",
            ]
        )
        return "\n".join(lines)
