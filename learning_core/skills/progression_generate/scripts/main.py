from __future__ import annotations

from learning_core.contracts.progression import ProgressionArtifact, ProgressionGenerationRequest
from learning_core.runtime.policy import ExecutionPolicy
from learning_core.skills.base import StructuredOutputSkill
from learning_core.skills.prompt_utils import append_user_authored_context


def _format_optional(value: object | None) -> str:
    if value is None:
        return "unknown"
    if isinstance(value, list):
        return ", ".join(str(item) for item in value) or "none"
    return str(value)


def _format_bool(value: bool | None) -> str:
    if value is None:
        return "unknown"
    return "yes" if value else "no"


class ProgressionGenerateSkill(StructuredOutputSkill):
    name = "progression_generate"
    input_model = ProgressionGenerationRequest
    output_model = ProgressionArtifact
    policy = ExecutionPolicy(
        skill_name="progression_generate",
        skill_version="2026-04-19.2",
        max_tokens=8000,
    )

    def build_user_prompt(self, payload: ProgressionGenerationRequest, context) -> str:
        skill_list = "\n".join(
            [
                f'{index + 1}. EXACT skillRef: "{item.skillRef}"\n'
                f"   outputRule: copy this exact skillRef string verbatim anywhere it appears in phases or edges\n"
                f'   title: "{item.title}"\n'
                f"   ordinal: {_format_optional(item.ordinal)}"
                + (f'\n   domain: "{item.domainTitle}"' if item.domainTitle else "")
                + (f'\n   strand: "{item.strandTitle}"' if item.strandTitle else "")
                + (f'\n   goalGroup: "{item.goalGroupTitle}"' if item.goalGroupTitle else "")
                + (f'\n   unitRef: "{item.unitRef}"' if item.unitRef else "")
                + (f'\n   unitTitle: "{item.unitTitle}"' if item.unitTitle else "")
                + (f"\n   unitOrderIndex: {item.unitOrderIndex}" if item.unitOrderIndex is not None else "")
                + (
                    f'\n   instructionalRole: "{item.instructionalRole}"'
                    if item.instructionalRole
                    else ""
                )
                + f"\n   requiresAdultSupport: {_format_bool(item.requiresAdultSupport)}"
                + f"\n   safetyCritical: {_format_bool(item.safetyCritical)}"
                + f"\n   isAuthenticApplication: {_format_bool(item.isAuthenticApplication)}"
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
            f"- Grade levels: {_format_optional(payload.gradeLevels)}",
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
            "Pacing + phase-budget guidance:",
            f"- Total weeks: {_format_optional(payload.totalWeeks)}",
            f"- Sessions per week: {_format_optional(payload.sessionsPerWeek)}",
            f"- Session minutes: {_format_optional(payload.sessionMinutes)}",
            f"- Total sessions: {_format_optional(payload.totalSessions)}",
            f"- Suggested phase-count range: {_format_optional(payload.suggestedPhaseCountMin)} to {_format_optional(payload.suggestedPhaseCountMax)}",
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
            "",
            "Requirements / checklist:",
            "- Treat source-authored order as a strong prior; depart only for true prerequisites, safety, or clearly task-first/authentic-performance reasons.",
            "- Assign every skillRef to exactly one phase.",
            "- Use only the provided skillRefs.",
            "- Do not invent skillRefs or omit skillRefs.",
            "- Every phase must have a non-empty, meaningful description.",
            "- Use revisitAfter deliberately for retention, fluency, and retrieval support.",
            "- Keep phases schedulable; avoid micro-phases and giant catch-all phases.",
            "- Keep hardPrerequisite edges acyclic.",
            "- Do not point hardPrerequisite or recommendedBefore from a later phase to an earlier phase.",
            "- Prefer sparse, meaningful edges over dense graphs.",
            "- Skills remain the graph nodes.",
            "- Use unit anchors as authored sequencing evidence and cohesion boundaries, not as replacement nodes.",
            "- Use the output schema exactly.",
            "- For every phases[].skillRefs entry and every edges[].fromSkillRef / edges[].toSkillRef value, the only acceptable output is an exact verbatim copy of a provided skillRef.",
        ]
        append_user_authored_context(lines, context)
        lines.extend(["", "Generate the progression graph."])
        return "\n".join(lines)
