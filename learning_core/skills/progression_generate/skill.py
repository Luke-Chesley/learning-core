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
        skill_version="2026-04-09",
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
        lines = [
            f"Active learner: {payload.learnerName}",
            "",
            "Curriculum:",
            f"- Title: {payload.sourceTitle}",
            f"- Summary: {payload.sourceSummary or 'None'}",
            "",
            f"Authoritative skill catalog ({len(payload.skillCatalog)} skills):",
            skill_list or "No skills provided.",
            "",
            "Requirements:",
            "- Put every skillRef in exactly one phase.",
            "- Use only the skillRefs above.",
            "- Do not invent refs.",
            "- Do not omit refs.",
            "- Keep hardPrerequisite edges acyclic.",
            "- Prefer sparse, meaningful edges.",
            "- Use the output schema exactly.",
        ]
        append_user_authored_context(lines, context)
        lines.extend(["", "Generate the progression graph."])
        return "\n".join(lines)
