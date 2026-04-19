from __future__ import annotations

from learning_core.contracts.progression import ProgressionArtifact, ProgressionGenerationRequest
from learning_core.runtime.policy import ExecutionPolicy
from learning_core.skills.base import StructuredOutputSkill
from learning_core.skills.prompt_utils import append_user_authored_context


class ProgressionGenerateSkill(StructuredOutputSkill):
    name = "progression_generate"
    input_model = ProgressionGenerationRequest
    output_model = ProgressionArtifact
    policy = ExecutionPolicy(
        skill_name="progression_generate",
        skill_version="2026-04-19",
        max_tokens=8000,
    )

    def build_user_prompt(self, payload: ProgressionGenerationRequest, context) -> str:
        skill_list = "\n".join(
            [
                f'{index + 1}. skillRef: "{item.skillRef}"\n'
                f'   title: "{item.title}"'
                + (f'\n   domain: "{item.domainTitle}"' if item.domainTitle else "")
                + (f'\n   strand: "{item.strandTitle}"' if item.strandTitle else "")
                + (f'\n   goalGroup: "{item.goalGroupTitle}"' if item.goalGroupTitle else "")
                for index, item in enumerate(payload.skillCatalog)
            ]
        )
        unit_anchor_list = "\n".join(
            [
                f'{index + 1}. unitRef: "{item.unitRef}"\n'
                f'   title: "{item.title}"\n'
                f'   orderIndex: {item.orderIndex}\n'
                f'   skillRefs: {item.skillRefs}'
                for index, item in enumerate(payload.unitAnchors)
            ]
        )
        lines = [
            f"Active learner: {payload.learnerName}",
            "",
            "Curriculum:",
            f"- Title: {payload.sourceTitle}",
            f"- Summary: {payload.sourceSummary or 'None'}",
            f"- Request mode: {payload.requestMode or 'unknown'}",
            f"- Source kind: {payload.sourceKind or 'unknown'}",
            f"- Delivery pattern: {payload.deliveryPattern or 'unknown'}",
            f"- Entry strategy: {payload.entryStrategy or 'unknown'}",
            f"- Continuation mode: {payload.continuationMode or 'unknown'}",
            "",
            f"Authoritative skill catalog ({len(payload.skillCatalog)} skills):",
            skill_list or "No skills provided.",
            "",
            f"Unit anchors ({len(payload.unitAnchors)} units):",
            unit_anchor_list or "No unit anchors provided.",
            "",
            "Requirements:",
            "- Put every skillRef in exactly one phase.",
            "- Use only the skillRefs above.",
            "- Do not invent refs.",
            "- Do not omit refs.",
            "- Keep hardPrerequisite edges acyclic.",
            "- Prefer sparse, meaningful edges.",
            "- Skills remain the graph nodes.",
            "- Use unit anchors only as broad sequencing evidence, not as replacement nodes.",
            "- Favor prerequisite logic over curriculum prose.",
            "- Use the output schema exactly.",
        ]
        append_user_authored_context(lines, context)
        lines.extend(["", "Generate the progression graph."])
        return "\n".join(lines)
