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
        lesson_anchor_list = "\n".join(
            [
                f'{index + 1}. lessonRef: "{item.lessonRef}"\n'
                f'   unitRef: "{item.unitRef}"\n'
                f'   title: "{item.title}"\n'
                f'   lessonType: "{item.lessonType}"\n'
                f"   orderIndex: {item.orderIndex}\n"
                f'   linkedSkillRefs: {item.linkedSkillRefs}'
                for index, item in enumerate(payload.lessonAnchors)
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
            f"Lesson anchors ({len(payload.lessonAnchors)} lessons):",
            lesson_anchor_list or "No lesson anchors provided.",
            "",
            "Requirements:",
            "- Put every skillRef in exactly one phase.",
            "- Use only the skillRefs above.",
            "- Do not invent refs.",
            "- Do not omit refs.",
            "- Keep hardPrerequisite edges acyclic.",
            "- Prefer sparse, meaningful edges.",
            "- Skills remain the graph nodes; lesson anchors are sequencing evidence, not replacement nodes.",
            "- Respect launchPlan.openingLessonRefs and launchPlan.openingSkillRefs as the opening window when they are present.",
            "- If deliveryPattern is task_first, keep the opening arc anchored in authentic tasks or projects and backfill prerequisite concepts just in time.",
            "- If lesson anchors link skills into the opening window, avoid front-loading distant skills ahead of those launch skills unless a true prerequisite is required.",
            "- Use the output schema exactly.",
        ]
        if payload.launchPlan:
            lines.extend(
                [
                    "",
                    "Launch plan:",
                    f"- Recommended horizon: {payload.launchPlan.recommendedHorizon}",
                    f"- Scope summary: {payload.launchPlan.scopeSummary}",
                    f"- Initial slice used: {payload.launchPlan.initialSliceUsed}",
                    f"- Initial slice label: {payload.launchPlan.initialSliceLabel or 'None'}",
                    f"- Launch entry strategy: {payload.launchPlan.entryStrategy or 'None'}",
                    f"- Launch continuation mode: {payload.launchPlan.continuationMode or 'None'}",
                    f"- Opening lesson refs: {payload.launchPlan.openingLessonRefs}",
                    f"- Opening skill refs: {payload.launchPlan.openingSkillRefs}",
                ]
            )
        append_user_authored_context(lines, context)
        lines.extend(["", "Generate the progression graph."])
        return "\n".join(lines)
