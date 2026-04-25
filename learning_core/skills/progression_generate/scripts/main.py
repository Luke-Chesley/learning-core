from __future__ import annotations

import json
from difflib import SequenceMatcher

from learning_core.contracts.progression import ProgressionArtifact, ProgressionGenerationRequest
from learning_core.observability.traces import PromptPreview
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


def _repair_skill_ref(skill_ref: str, catalog_refs: set[str]) -> str:
    if skill_ref in catalog_refs:
        return skill_ref

    slug = skill_ref.rsplit("/", 1)[-1]
    matches = [candidate for candidate in catalog_refs if candidate.rsplit("/", 1)[-1] == slug]
    if len(matches) == 1:
        return matches[0]

    suffix_matches = [candidate for candidate in catalog_refs if candidate.endswith(f"/{slug}")]
    if len(suffix_matches) == 1:
        return suffix_matches[0]

    similar_slug_matches = [
        candidate
        for candidate in catalog_refs
        if SequenceMatcher(None, slug, candidate.rsplit("/", 1)[-1]).ratio() >= 0.82
    ]
    if len(similar_slug_matches) == 1:
        return similar_slug_matches[0]

    return skill_ref


class ProgressionGenerateSkill(StructuredOutputSkill):
    name = "progression_generate"
    input_model = ProgressionGenerationRequest
    output_model = ProgressionArtifact
    policy = ExecutionPolicy(
        skill_name="progression_generate",
        skill_version="2026-04-19.2",
        max_tokens=8000,
    )

    def repair_invalid_artifact(self, *, raw_artifact, payload, context, error):
        del context, error
        if not isinstance(raw_artifact, dict):
            return None

        phases = raw_artifact.get("phases")
        if not isinstance(phases, list):
            return None

        catalog_refs = {item.skillRef for item in payload.skillCatalog}
        seen: set[str] = set()
        repaired_phases: list[dict] = []
        changed = False

        for phase in phases:
            if not isinstance(phase, dict):
                return None
            skill_refs = phase.get("skillRefs")
            if not isinstance(skill_refs, list):
                return None

            repaired_refs: list[object] = []
            for skill_ref in skill_refs:
                if not isinstance(skill_ref, str):
                    repaired_refs.append(skill_ref)
                    continue
                repaired_ref = _repair_skill_ref(skill_ref, catalog_refs)
                changed = changed or repaired_ref != skill_ref
                if repaired_ref not in catalog_refs:
                    repaired_refs.append(repaired_ref)
                    continue
                if repaired_ref in seen:
                    changed = True
                    continue
                seen.add(repaired_ref)
                repaired_refs.append(repaired_ref)

            if repaired_refs:
                repaired_phases.append({**phase, "skillRefs": repaired_refs})
            else:
                changed = True

        edges = raw_artifact.get("edges")
        repaired_edges: list[dict] | object = edges
        if isinstance(edges, list):
            repaired_edges = []
            for edge in edges:
                if not isinstance(edge, dict):
                    repaired_edges.append(edge)
                    continue
                repaired_edge = dict(edge)
                for key in ("fromSkillRef", "toSkillRef"):
                    value = repaired_edge.get(key)
                    if isinstance(value, str):
                        repaired_value = _repair_skill_ref(value, catalog_refs)
                        changed = changed or repaired_value != value
                        repaired_edge[key] = repaired_value
                repaired_edges.append(repaired_edge)

        if not changed:
            return None

        return {**raw_artifact, "phases": repaired_phases, "edges": repaired_edges}

    def validate_artifact_semantics(self, *, artifact: ProgressionArtifact, payload, context) -> list[str]:
        del context
        expected = [item.skillRef for item in payload.skillCatalog]
        actual = [skill_ref for phase in artifact.phases for skill_ref in phase.skillRefs]

        missing = [skill_ref for skill_ref in expected if skill_ref not in actual]
        invented = [skill_ref for skill_ref in actual if skill_ref not in expected]
        duplicates = sorted({skill_ref for skill_ref in actual if actual.count(skill_ref) > 1})

        issues: list[str] = []
        if missing:
            issues.append(f"progression missing skillRefs: {', '.join(missing)}")
        if invented:
            issues.append(f"progression invented skillRefs: {', '.join(invented)}")
        if duplicates:
            issues.append(f"progression duplicated skillRefs: {', '.join(duplicates)}")
        return issues

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
            "- Do not create a review, transfer, or capstone phase by repeating skillRefs that already appeared in earlier phases.",
            "- Represent review, retrieval, fluency, and later practice with revisitAfter edges, not by duplicating phase membership.",
            "- Use only the provided skillRefs.",
            "- Do not invent skillRefs or omit skillRefs.",
            "- Every phase must have a non-empty, meaningful description.",
            "- Use revisitAfter deliberately for retention, fluency, and retrieval support.",
            "- Keep phases schedulable; tiny curricula may have one or two compact phases, while larger curricula should avoid micro-phases and giant catch-all phases.",
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

    def build_validation_retry_preview(
        self,
        *,
        payload: ProgressionGenerationRequest,
        context,
        raw_artifact,
        error,
    ) -> PromptPreview:
        raw_json = json.dumps(raw_artifact, indent=2, default=str)
        skill_refs = "\n".join(f'- "{item.skillRef}"' for item in payload.skillCatalog)
        return PromptPreview(
            system_prompt=self.read_skill_markdown(),
            user_prompt="\n".join(
                [
                    self.build_user_prompt(payload, context),
                    "",
                    "The previous JSON did not validate against the progression graph contract.",
                    "Return one corrected JSON object only. Preserve the intended ordering while fixing schema violations.",
                    "",
                    "Validation error:",
                    str(error),
                    "",
                    "Authoritative skillRefs:",
                    skill_refs,
                    "",
                    "Correction rules:",
                    "- Each provided skillRef must appear in exactly one phases[].skillRefs array.",
                    "- Never repeat a skillRef in a later review, transfer, capstone, or catch-all phase.",
                    "- If a skill should be revisited later, add a revisitAfter edge instead of duplicating it in another phase.",
                    "- Drop any phase that becomes empty after removing duplicate skillRefs.",
                    "- Keep hardPrerequisite edges acyclic and remove self-loop or duplicate edges.",
                    "",
                    "Previous invalid JSON:",
                    raw_json,
                ]
            ),
        )
