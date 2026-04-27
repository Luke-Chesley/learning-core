from __future__ import annotations

import json
from typing import Any

from learning_core.contracts.teaching_guide import (
    TeachingGuideArtifact,
    TeachingGuideGenerationRequest,
)
from learning_core.runtime.policy import ExecutionPolicy
from learning_core.skills.base import StructuredOutputSkill
from learning_core.skills.prompt_utils import append_user_authored_context


def _dump_section(value: Any) -> str:
    if value in (None, [], {}):
        return "not provided"
    return json.dumps(value, indent=2, sort_keys=True)


class TeachingGuideGenerateSkill(StructuredOutputSkill):
    name = "teaching_guide_generate"
    input_model = TeachingGuideGenerationRequest
    output_model = TeachingGuideArtifact
    policy = ExecutionPolicy(
        skill_name="teaching_guide_generate",
        skill_version="2026-04-27",
        task_kind="generation",
        temperature=0.25,
        max_tokens=4500,
        latency_class="interactive",
    )

    def build_user_prompt(self, payload: TeachingGuideGenerationRequest, context) -> str:
        lines = [
            f"Schema version: {payload.schema_version}",
            f"Guidance mode: {payload.guidance_mode}",
            "Audience: parent",
            "",
            "Lesson basis:",
            _dump_section(payload.lesson),
            "",
            "Existing session artifact, if provided:",
            _dump_section(payload.existing_session_artifact),
            "",
            "Source context:",
            _dump_section(payload.source_context),
            "",
            "Route items:",
            _dump_section(payload.route_items),
            "",
            "Learner context:",
            _dump_section(payload.learner_context),
            "",
            "Teacher context:",
            _dump_section(payload.teacher_context),
            "",
            "Activity summary:",
            _dump_section(payload.activity_summary),
            "",
            "State reporting context:",
            _dump_section(payload.state_reporting_context),
            "",
            "Requirements:",
            "- Generate a parent-facing teaching guide, not a learner activity.",
            "- Use only facts present in the supplied basis.",
            "- If the basis is thin, set outsource_flags and adult_review_required instead of filling gaps.",
            "- Keep each field short and scannable.",
            "- For preteach mode, include at least two guided_questions unless adult_review_required is true or source context is thin.",
            "- Include common misconceptions when the basis supports them.",
            "- Every misconception repair must include exactly three easier_examples.",
            "- Do not include legal compliance, accreditation, school approval, state-law certainty, diagnosis, or AI-teacher claims.",
        ]
        append_user_authored_context(lines, context)
        lines.extend(["", "Generate the teaching guide artifact."])
        return "\n".join(lines)

    def repair_invalid_artifact(self, *, raw_artifact, payload, context, error):
        if not isinstance(raw_artifact, dict):
            return None

        repaired = dict(raw_artifact)
        repaired["audience"] = "parent"
        repaired.setdefault("guidance_mode", payload.guidance_mode)
        repaired.setdefault("adult_review_required", False)

        flags = repaired.get("outsource_flags")
        if not isinstance(flags, list):
            repaired["outsource_flags"] = []

        misconceptions = repaired.get("common_misconceptions")
        if isinstance(misconceptions, list):
            repaired_misconceptions = []
            for item in misconceptions:
                if not isinstance(item, dict):
                    continue
                fixed = dict(item)
                examples = fixed.get("easier_examples")
                if isinstance(examples, list):
                    examples = [str(example) for example in examples if str(example).strip()]
                else:
                    examples = []
                while len(examples) < 3:
                    examples.append("Use a simpler example from the provided lesson.")
                fixed["easier_examples"] = examples[:3]
                repaired_misconceptions.append(fixed)
            repaired["common_misconceptions"] = repaired_misconceptions

        return repaired

    def validate_artifact_semantics(self, *, artifact, payload, context) -> list[str]:
        issues: list[str] = []
        if artifact.audience != "parent":
            issues.append("audience must be parent")
        if artifact.guidance_mode != payload.guidance_mode:
            issues.append("guidance_mode must match the request")
        return issues
