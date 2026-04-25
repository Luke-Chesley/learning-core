from __future__ import annotations

from learning_core.contracts.launch_plan import LaunchPlanArtifact, LaunchPlanGenerationRequest
from learning_core.runtime.policy import ExecutionPolicy
from learning_core.skills.base import StructuredOutputSkill
from learning_core.skills.prompt_utils import append_user_authored_context


class LaunchPlanGenerateSkill(StructuredOutputSkill):
    name = "launch_plan_generate"
    input_model = LaunchPlanGenerationRequest
    output_model = LaunchPlanArtifact
    policy = ExecutionPolicy(
        skill_name="launch_plan_generate",
        skill_version="2026-04-20",
        max_tokens=6000,
    )

    def build_user_prompt(self, payload: LaunchPlanGenerationRequest, context) -> str:
        skill_list = "\n".join(
            [
                f'{index + 1}. skillRef: "{item.skillRef}"\n'
                f'   title: "{item.title}"'
                for index, item in enumerate(payload.skillCatalog)
            ]
        )
        unit_list = "\n".join(
            [
                f'{index + 1}. unitRef: "{item.unitRef}"\n'
                f'   title: "{item.title}"\n'
                f'   orderIndex: {item.orderIndex}\n'
                f'   skillRefs: {item.skillRefs}'
                for index, item in enumerate(payload.unitAnchors)
            ]
        )
        phase_list = "\n".join(
            [
                f'{index + 1}. phase: "{phase.title}"\n'
                f'   skillRefs: {phase.skillRefs}'
                for index, phase in enumerate(payload.progression.phases)
            ]
        ) if payload.progression else "No progression provided."
        lines = [
            f"Active learner: {payload.learnerName}",
            f"Curriculum title: {payload.sourceTitle}",
            f"Curriculum summary: {payload.sourceSummary or 'None'}",
            f"Request mode: {payload.requestMode or 'unknown'}",
            f"Source kind: {payload.sourceKind or 'unknown'}",
            f"Delivery pattern: {payload.deliveryPattern or 'unknown'}",
            f"Entry strategy: {payload.entryStrategy or 'unknown'}",
            f"Entry label: {payload.entryLabel or 'None'}",
            f"Continuation mode: {payload.continuationMode or 'unknown'}",
            f"Chosen horizon: {payload.chosenHorizon}",
            "",
            f"Authoritative skill catalog ({len(payload.skillCatalog)} skills):",
            skill_list,
            "",
            f"Unit anchors ({len(payload.unitAnchors)} units):",
            unit_list,
            "",
            "Progression basis:",
            phase_list,
            "",
            "Requirements:",
            "- Treat this as an optional opening-window selector, not as the canonical curriculum-creation path.",
            "- Return a bounded opening slice only.",
            "- Use only unitRefs and skillRefs from the provided basis.",
            "- Do not invent refs.",
            "- openingSkillRefs must contain only canonical skill refs.",
            "- Do not return openingUnitRefs; the app derives owning units from openingSkillRefs.",
            "- Keep the opening slice small enough for the chosen horizon.",
            "- Favor the earliest teachable unit arc unless the source metadata clearly points elsewhere.",
            "- Respect the chosen horizon exactly; do not reinterpret it.",
        ]
        append_user_authored_context(lines, context)
        lines.extend(["", "Generate the optional launch window."])
        return "\n".join(lines)
