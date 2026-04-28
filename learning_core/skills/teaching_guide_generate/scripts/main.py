from __future__ import annotations

import json
from typing import Any

from learning_core.contracts.teaching_guide import (
    TeachingGuideArtifact,
    TeachingGuideGenerationRequest,
)
from learning_core.observability.traces import PromptPreview
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

    def _contract_summary(self) -> str:
        return "\n".join(
            [
                "Required TeachingGuideArtifact fields:",
                "- title: string",
                "- audience: parent",
                "- guidance_mode: requested mode",
                "- lesson_focus: string",
                "- parent_brief: { summary, why_it_matters?, time_needed_minutes?, materials }",
                "- teach_it: { setup, steps, vocabulary, worked_example? }",
                "- teach_it.vocabulary: [{ term, definition, use_in_sentence? }]",
                "- guided_questions: [{ question, listen_for, follow_up? }]",
                "- common_misconceptions: [{ misconception, why_it_happens?, repair_move, easier_examples: string[3] }]",
                "- practice_plan: { quick_warmup?, parent_moves, independent_try? }",
                "- check_understanding: { prompts, evidence_of_understanding, if_stuck?, if_ready? }",
                "- adaptation_moves: [{ signal, move }]",
                "- recordkeeping: [{ note, evidence_to_save? }]",
                "- outsource_flags: string[]",
                "- adult_review_required: boolean",
            ]
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
            "",
            self._contract_summary(),
        ]
        append_user_authored_context(lines, context)
        lines.extend(["", "Generate the teaching guide artifact."])
        return "\n".join(lines)

    def repair_invalid_artifact(self, *, raw_artifact, payload, context, error):
        return None

    def build_validation_retry_preview(
        self,
        *,
        payload: TeachingGuideGenerationRequest,
        context,
        raw_artifact,
        error,
    ):
        raw_json = json.dumps(raw_artifact, indent=2, default=str)
        return PromptPreview(
            system_prompt=self.read_skill_markdown(),
            user_prompt="\n".join(
                [
                    self.build_user_prompt(payload, context),
                    "",
                    "The previous JSON did not validate against the TeachingGuideArtifact contract.",
                    "Return one corrected JSON object only. Preserve the intended teaching support while fixing schema violations.",
                    "",
                    "Validation error:",
                    str(error),
                    "",
                    "Correction rules:",
                    "- Use the exact top-level fields in the contract summary.",
                    "- `guided_questions` must contain objects, not strings.",
                        "- `common_misconceptions` must contain objects, not strings.",
                        "- `teach_it.vocabulary` items must use `definition`, not `simple_definition`.",
                        "- Each misconception object must include exactly three `easier_examples`.",
                    "- Use `parent_brief`, `teach_it`, `practice_plan`, and `check_understanding`; do not replace them with informal field names.",
                    "- Do not add fields outside the contract.",
                    "",
                    "Previous invalid JSON:",
                    raw_json,
                ]
            ),
        )

    def validate_artifact_semantics(self, *, artifact, payload, context) -> list[str]:
        issues: list[str] = []
        if artifact.audience != "parent":
            issues.append("audience must be parent")
        if artifact.guidance_mode != payload.guidance_mode:
            issues.append("guidance_mode must match the request")
        return issues
