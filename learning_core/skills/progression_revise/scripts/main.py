from __future__ import annotations

from learning_core.contracts.progression import ProgressionArtifact, ProgressionRevisionRequest
from learning_core.runtime.policy import ExecutionPolicy
from learning_core.skills.base import StructuredOutputSkill
from learning_core.skills.prompt_utils import append_user_authored_context


class ProgressionReviseSkill(StructuredOutputSkill):
    name = "progression_revise"
    input_model = ProgressionRevisionRequest
    output_model = ProgressionArtifact
    policy = ExecutionPolicy(
        skill_name="progression_revise",
        skill_version="2026-04-20",
        max_tokens=8000,
    )

    def build_user_prompt(self, payload: ProgressionRevisionRequest, context) -> str:
        skill_list = "\n".join(
            [
                f'{index + 1}. EXACT skillRef: "{item.skillRef}"\n'
                f"   outputRule: copy this exact skillRef string verbatim anywhere it appears in phases or edges\n"
                f'   title: "{item.title}"'
                + (f'\n   domain: "{item.domainTitle}"' if item.domainTitle else "")
                + (f'\n   strand: "{item.strandTitle}"' if item.strandTitle else "")
                + (f'\n   goalGroup: "{item.goalGroupTitle}"' if item.goalGroupTitle else "")
                + (f'\n   unitRef: "{item.unitRef}"' if item.unitRef else "")
                + (f'\n   unitTitle: "{item.unitTitle}"' if item.unitTitle else "")
                + (f"\n   unitOrderIndex: {item.unitOrderIndex}" if item.unitOrderIndex is not None else "")
                for index, item in enumerate(payload.skillCatalog)
            ]
        )
        unit_anchor_list = "\n".join(
            [
                f'{index + 1}. unitRef: "{item.unitRef}"\n'
                f'   title: "{item.title}"\n'
                f'   description: "{item.description}"\n'
                f"   orderIndex: {item.orderIndex}"
                + (
                    f"\n   estimatedWeeks: {item.estimatedWeeks}"
                    if item.estimatedWeeks is not None
                    else ""
                )
                + (
                    f"\n   estimatedSessions: {item.estimatedSessions}"
                    if item.estimatedSessions is not None
                    else ""
                )
                + f"\n   skillRefs: {item.skillRefs}"
                for index, item in enumerate(payload.unitAnchors)
            ]
        )
        lines = [
            "Learner / context:",
            f"- Active learner: {payload.learnerName}",
            f"- Learner prior knowledge: {payload.learnerPriorKnowledge or 'unknown'}",
            f"- Grade levels: {', '.join(payload.gradeLevels) if payload.gradeLevels else 'unknown'}",
            "",
            "Curriculum / source metadata:",
            f"- Title: {payload.sourceTitle}",
            f"- Summary: {payload.sourceSummary or 'None'}",
            f"- Request mode: {payload.requestMode or 'unknown'}",
            f"- Source kind: {payload.sourceKind or 'unknown'}",
            f"- Delivery pattern: {payload.deliveryPattern or 'unknown'}",
            f"- Entry strategy: {payload.entryStrategy or 'unknown'}",
            f"- Continuation mode: {payload.continuationMode or 'unknown'}",
            "",
            "Pacing + structure guidance:",
            f"- Total weeks: {payload.totalWeeks if payload.totalWeeks is not None else 'unknown'}",
            f"- Sessions per week: {payload.sessionsPerWeek if payload.sessionsPerWeek is not None else 'unknown'}",
            f"- Session minutes: {payload.sessionMinutes if payload.sessionMinutes is not None else 'unknown'}",
            f"- Total sessions: {payload.totalSessions if payload.totalSessions is not None else 'unknown'}",
            "",
            f"Authoritative skill catalog ({len(payload.skillCatalog)} skills):",
            skill_list or "No skills provided.",
            "",
            "Exact output construction rule for skillRefs:",
            "- The only acceptable skillRef strings in the output are the exact strings printed above after \"EXACT skillRef:\".",
            "- When a phase or edge needs a skillRef, copy that exact string verbatim from the authoritative skill catalog.",
            "- Do not reconstruct, normalize, shorten, prepend, append, or rewrite a skillRef from domain, strand, goalGroup, title, unit metadata, or any other label.",
            "- Never combine path segments from metadata to build a new skillRef.",
            "",
            f"Ordered unit anchors ({len(payload.unitAnchors)} units):",
            unit_anchor_list or "No unit anchors provided.",
        ]
        if payload.revisionRequest:
            lines.extend(["", f"Revision request: {payload.revisionRequest}"])
        append_user_authored_context(lines, context)
        lines.extend(
            [
                "",
                "Requirements:",
                "- Preserve authored unit order unless a real prerequisite, safety, or authentic-performance reason justifies changing it.",
                "- Assign every skillRef to exactly one phase.",
                "- Use only the provided skillRefs.",
                "- Every phase must have a non-empty, meaningful description.",
                "- Keep hardPrerequisite edges acyclic.",
                "- Prefer sparse, meaningful edges.",
                "- Do not point hardPrerequisite or recommendedBefore from a later phase to an earlier phase unless the reorder is clearly justified.",
                "",
                "Generate the revised progression graph.",
            ]
        )
        return "\n".join(lines)
