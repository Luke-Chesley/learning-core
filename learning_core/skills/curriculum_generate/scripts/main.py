from __future__ import annotations

from copy import deepcopy
import json
import re
from typing import Any

from learning_core.contracts.curriculum import CurriculumArtifact, CurriculumGenerationRequest
from learning_core.observability.traces import PromptPreview
from learning_core.runtime.policy import ExecutionPolicy
from learning_core.skills.base import StructuredOutputSkill
from learning_core.skills.prompt_utils import (
    append_user_authored_context,
    build_openai_file_blocks,
    format_curriculum_transcript,
    format_source_files,
)


class CurriculumGenerateSkill(StructuredOutputSkill):
    name = "curriculum_generate"
    input_model = CurriculumGenerationRequest
    output_model = CurriculumArtifact
    policy = ExecutionPolicy(
        skill_name="curriculum_generate",
        skill_version="2026-04-19",
        max_tokens=32000,
    )

    def _explicit_total_sessions(self, payload: CurriculumGenerationRequest) -> int | None:
        if payload.planningConstraints and payload.planningConstraints.totalSessions is not None:
            return payload.planningConstraints.totalSessions

        candidate_text = " ".join(
            value
            for value in [
                payload.entryLabel or "",
                payload.sourceText or "",
                " ".join(payload.detectedChunks or []),
            ]
            if value
        )
        match = re.search(r"\b(\d{1,3})\s+(?:sessions?|days?)\b", candidate_text, re.IGNORECASE)
        if not match:
            return None
        parsed = int(match.group(1))
        return parsed if parsed > 0 else None

    def _soft_pacing_total_sessions(self, payload: CurriculumGenerationRequest) -> int | None:
        constraints = payload.planningConstraints
        if not constraints or constraints.totalSessions is not None:
            return None
        if constraints.totalWeeks is None or constraints.sessionsPerWeek is None:
            return None
        return constraints.totalWeeks * constraints.sessionsPerWeek

    def _has_exact_session_count(self, payload: CurriculumGenerationRequest) -> bool:
        return self._explicit_total_sessions(payload) is not None

    def _large_session_sequence_guidance(self, payload: CurriculumGenerationRequest) -> list[str]:
        total_sessions = self._explicit_total_sessions(payload)
        if total_sessions is None or total_sessions < 20:
            return []
        return [
            "Large exact-session artifact compactness contract:",
            f"- This request has {total_sessions} sessions. Preserve all {total_sessions} sessions, but keep each object compact.",
            "- Use exactly one primary skill, one content anchor, one teachable item, and one deliverySequence item per session unless the source explicitly requires more.",
            "- Keep titles specific and short; put the concrete curriculum substance in the anchor summary, namedAnchors, vocabulary, misconception, assessmentCue, and sessionFocus.",
            "- contentAnchors[].details should contain at most two short details for large session sequences.",
            "- teachableItems[].parentNotes, misconceptions, and deliverySequence[].evidenceToSave should usually contain one or two short entries.",
            "- Do not include unspecified metadata such as academicYear.",
            "- Do not write long rationales, long summaries, or repeated prose; compactness is part of the contract for large session_sequence artifacts.",
        ]

    def _pacing_contract_guidance(self, payload: CurriculumGenerationRequest) -> list[str]:
        lines = [
            "Pacing contract:",
            "- Always emit positive integers for pacing.totalWeeks, pacing.sessionsPerWeek, pacing.sessionMinutes, and pacing.totalSessions.",
            "- Preserve explicit parent/source pacing constraints exactly when present.",
            "- If any pacing value is missing, choose a conservative assumption from the request horizon, cadence language, learner needs, and scope.",
            "- Explain inferred pacing assumptions in pacing.coverageNotes.",
            "- pacing.totalSessions should normally equal pacing.totalWeeks * pacing.sessionsPerWeek; explain any irregular cadence in coverageNotes.",
            "- pacing.sessionMinutes is the expected parent-led learning block for one session.",
            "- For short horizons, narrow or defer content before overloading individual sessions.",
            "- Do not plan more than 10 new durable skills per week unless the source explicitly requires it; defer extra scope in coverageNotes.",
        ]
        if payload.requestMode == "source_entry" and payload.planningConstraints:
            constraints = payload.planningConstraints
            explicit_values = {
                "totalSessions": constraints.totalSessions,
                "totalWeeks": constraints.totalWeeks,
                "sessionsPerWeek": constraints.sessionsPerWeek,
                "sessionMinutes": constraints.sessionMinutes,
            }
            present = [
                f"{key}={value}"
                for key, value in explicit_values.items()
                if value is not None
            ]
            if present:
                lines.append(f"- Explicit planningConstraints to preserve: {', '.join(present)}.")
            soft_total_sessions = self._soft_pacing_total_sessions(payload)
            if soft_total_sessions is not None:
                lines.extend(
                    [
                        f"- Inferred pacing budget: totalWeeks x sessionsPerWeek suggests about {soft_total_sessions} sessions.",
                        "- Because planningConstraints.totalSessions is not explicit, treat that as scale guidance, not a rigid request for one generated skill per session.",
                        "- Do not collapse a seasonal or multiweek curriculum request into a two-week starter when totalWeeks/sessionsPerWeek are present.",
                    ]
                )
        elif payload.requestMode == "conversation_intake" and payload.pacingExpectations:
            expectations = payload.pacingExpectations
            present = [
                f"{key}={value}"
                for key, value in {
                    "totalWeeks": expectations.totalWeeks,
                    "sessionsPerWeek": expectations.sessionsPerWeek,
                    "sessionMinutes": expectations.sessionMinutes,
                    "totalSessionsLowerBound": expectations.totalSessionsLowerBound,
                    "totalSessionsUpperBound": expectations.totalSessionsUpperBound,
                }.items()
                if value is not None
            ]
            if present:
                lines.append(f"- Pacing expectations to honor: {', '.join(present)}.")
        return lines

    def _scale_guidance(self, payload: CurriculumGenerationRequest) -> str:
        if payload.requestMode == "source_entry":
            planning_constraints = payload.planningConstraints
            total_sessions = self._explicit_total_sessions(payload)
            if total_sessions is not None:
                return (
                    f"Use planningModel session_sequence. planningConstraints.totalSessions is {total_sessions}; "
                    "pacing.totalSessions and deliverySequence must preserve that number exactly. Create one concrete "
                    "deliverySequence item, teachable item, and primary skill per session."
                )
            if payload.sourceKind == "curriculum_request":
                soft_total_sessions = self._soft_pacing_total_sessions(payload)
                if soft_total_sessions is not None:
                    return (
                        "This is a parent-authored curriculum request with inferred horizon/cadence constraints. "
                        f"Use the stated totalWeeks and sessionsPerWeek as a real curriculum-scale budget of about {soft_total_sessions} sessions, "
                        "but do not force planningModel session_sequence unless planningConstraints.totalSessions is present. "
                        "Prefer content_map for flexible route planning, create enough distinct skills and teachableItems for the full multiweek arc, "
                        "and include review/application handles so downstream planning does not collapse the curriculum into a tiny starter."
                    )
                return (
                    "This is a parent-authored curriculum request. Build a concrete model-suggested curriculum map "
                    "from the stated topic, grade, learner context, and planningConstraints. Do not use planningModel "
                    "session_sequence unless planningConstraints.totalSessions or an exact session/day count is present; "
                    "otherwise choose content_map or source_sequence."
                )
            if payload.sourceKind == "timeboxed_plan":
                return (
                    "Use planningModel session_sequence. Preserve the requested session count; "
                    "deliverySequence must contain one concrete item per session. Use curriculumScale module "
                    "unless the timebox is only a single day or week."
                )
            if payload.sourceKind == "bounded_material":
                return (
                    "Keep the curriculum bounded, but choose planningModel single_lesson, content_map, "
                    "or session_sequence based on the source shape. Include concrete teachableItems and contentAnchors."
                )
            if payload.sourceKind == "comprehensive_source":
                return (
                    "Prefer curriculumScale reference_source or course with planningModel reference_map or source_sequence. "
                    "Represent the broader source with concrete content anchors rather than a shallow starter slice."
                )
            if payload.sourceKind == "structured_sequence":
                return (
                    "Use planningModel source_sequence unless an explicit session count calls for session_sequence. "
                    "Preserve the source order with concrete teachableItems."
                )
            if payload.recommendedHorizon in {"single_day", "few_days", "one_week"}:
                return (
                    "Prefer the smallest honest scale, but still include a teachable content map. "
                    "A compact curriculum does not need course-shaped hierarchy."
                )
            return (
                "Choose the smallest honest curriculumScale that still preserves the durable curriculum scope, "
                "and include concrete contentAnchors, teachableItems, and deliverySequence when the source is sequenced."
            )

        expectations = payload.pacingExpectations
        if expectations and expectations.totalWeeks is not None and expectations.totalWeeks <= 1:
            return "Prefer curriculumScale week and keep the structure compact; one unit can be enough, but it still needs concrete teachableItems."
        if expectations and expectations.totalSessionsUpperBound is not None and expectations.totalSessionsUpperBound <= 5:
            return "Prefer curriculumScale micro or week; avoid fake course hierarchy, but include concrete session/content detail."
        return (
            "Choose the smallest honest curriculumScale from the conversation, from micro/week through module/course, "
            "and make the content map concrete. Do not use planningModel session_sequence unless the conversation gives "
            "an exact session count or an authored numbered day/session sequence; a week or month horizon alone should "
            "usually be content_map or source_sequence."
        )

    def build_user_prompt(self, payload: CurriculumGenerationRequest, context) -> str:
        lines = [
            f"Active learner: {payload.learnerName}",
            f"Request mode: {payload.requestMode}",
            f"Title candidate: {payload.titleCandidate or 'None provided'}",
            f"Scale guidance: {self._scale_guidance(payload)}",
        ]

        if payload.requestMode == "source_entry":
            lines.extend(
                [
                    f"Requested route: {payload.requestedRoute or 'None provided'}",
                    f"Routed route: {payload.routedRoute or 'None provided'}",
                    "",
                    f"Source kind: {payload.sourceKind}",
                    f"Entry strategy: {payload.entryStrategy}",
                    f"Entry label: {payload.entryLabel or 'None provided'}",
                    f"Continuation mode: {payload.continuationMode}",
                    f"Delivery pattern: {payload.deliveryPattern}",
                    f"Recommended horizon: {payload.recommendedHorizon}",
                    "",
                    "Planning constraints:",
                    payload.planningConstraints.model_dump_json(indent=2)
                    if payload.planningConstraints
                    else "{}",
                    "",
                    "Assumptions:",
                    (payload.assumptions or []) and "\n".join(
                        f"- {value}" for value in (payload.assumptions or [])
                    )
                    or "- None provided",
                    "",
                    "Detected chunks:",
                    (payload.detectedChunks or []) and "\n".join(
                        f"- {value}" for value in (payload.detectedChunks or [])
                    )
                    or "- None provided",
                    "",
                    "Source packages:",
                    json.dumps(payload.sourcePackages, indent=2, default=lambda value: getattr(value, "model_dump", lambda: str(value))()),
                    "",
                    "Attached source files:",
                    format_source_files(payload.sourceFiles or []),
                    "",
                    "Primary source text:",
                    payload.sourceText or "",
                ]
            )
        else:
            lines.extend(
                [
                    "",
                    "Current requirement hints:",
                    json.dumps(payload.requirementHints or {}, indent=2),
                    "",
                    "Pacing expectations inferred from the conversation:",
                    payload.pacingExpectations.model_dump_json(indent=2)
                    if payload.pacingExpectations
                    else "{}",
                ]
            )

            if payload.granularityGuidance:
                lines.extend(
                    [
                        "",
                        "Granularity guidance:",
                        *[
                            f"{index + 1}. {note}"
                            for index, note in enumerate(payload.granularityGuidance)
                        ],
                    ]
                )

            lines.extend(
                [
                    "",
                    "Conversation transcript:",
                    format_curriculum_transcript(payload.messages or []),
                ]
            )

        if payload.correctionNotes:
            lines.extend(
                [
                    "",
                    "Correction notes for this retry:",
                    *[
                        f"{index + 1}. {note}"
                        for index, note in enumerate(payload.correctionNotes)
                    ],
                ]
            )

        append_user_authored_context(lines, context)
        lines.extend(
            [
                "",
                "Session sequence structural contract:",
                "- Treat IDs as a closed inventory: every referenced skillId, unitRef, anchorId, and teachableItemId must be declared in its matching top-level array.",
                "- Do not reference a future or convenient ID such as skill-7 unless that exact object exists in top-level skills.",
                "- If the request did not provide an exact total session/day count, do not use planningModel session_sequence.",
                "- If you choose planningModel session_sequence, every deliverySequence item is one concrete session.",
                "- Each session must reference a unique teachableItemId.",
                "- The first skillIds entry for each session is its primary skillId and must be unique across the deliverySequence.",
                "- If a broad concept repeats, create a narrower session-specific skill for the new review, practice, application, or project move.",
                "- The deliverySequence skillIds must be a subset of the referenced teachable item's skillIds.",
                *self._pacing_contract_guidance(payload),
                *self._large_session_sequence_guidance(payload),
                "",
                "Return the durable curriculum artifact only.",
            ]
        )
        return "\n".join(lines)

    def repair_invalid_artifact(self, *, raw_artifact, payload, context, error):
        del context
        if not isinstance(raw_artifact, dict):
            return None

        repaired = deepcopy(raw_artifact)
        changed = False

        if (
            repaired.get("planningModel") == "session_sequence"
            and not self._has_exact_session_count(payload)
        ):
            repaired["planningModel"] = "content_map"
            changed = True

        if self._repair_delivery_skill_membership(repaired):
            changed = True

        if repaired.get("planningModel") == "session_sequence" and self._repair_session_sequence_repeats(repaired):
            changed = True

        return repaired if changed else None

    def _repair_delivery_skill_membership(self, artifact: dict[str, Any]) -> bool:
        teachable_items = artifact.get("teachableItems")
        delivery_sequence = artifact.get("deliverySequence")
        if not isinstance(teachable_items, list) or not isinstance(delivery_sequence, list):
            return False

        item_by_id = {
            item.get("itemId"): item
            for item in teachable_items
            if isinstance(item, dict) and isinstance(item.get("itemId"), str)
        }
        changed = False
        for sequence_item in delivery_sequence:
            if not isinstance(sequence_item, dict):
                continue
            teachable_item = item_by_id.get(sequence_item.get("teachableItemId"))
            skill_ids = sequence_item.get("skillIds")
            if not isinstance(teachable_item, dict) or not isinstance(skill_ids, list):
                continue
            item_skill_ids = teachable_item.get("skillIds")
            if not isinstance(item_skill_ids, list):
                continue
            missing_skill_ids = [skill_id for skill_id in skill_ids if skill_id not in item_skill_ids]
            if not missing_skill_ids:
                continue
            teachable_item["skillIds"] = [*item_skill_ids, *missing_skill_ids]
            changed = True

            sequence_anchor_ids = sequence_item.get("contentAnchorIds")
            item_anchor_ids = teachable_item.get("contentAnchorIds")
            if isinstance(sequence_anchor_ids, list) and isinstance(item_anchor_ids, list):
                missing_anchor_ids = [
                    anchor_id for anchor_id in sequence_anchor_ids if anchor_id not in item_anchor_ids
                ]
                if missing_anchor_ids:
                    teachable_item["contentAnchorIds"] = [*item_anchor_ids, *missing_anchor_ids]

        return changed

    def _repair_session_sequence_repeats(self, artifact: dict[str, Any]) -> bool:
        skills = artifact.get("skills")
        units = artifact.get("units")
        teachable_items = artifact.get("teachableItems")
        delivery_sequence = artifact.get("deliverySequence")
        if not all(isinstance(value, list) for value in (skills, units, teachable_items, delivery_sequence)):
            return False

        skill_by_id = {
            skill.get("skillId"): skill
            for skill in skills
            if isinstance(skill, dict) and isinstance(skill.get("skillId"), str)
        }
        item_by_id = {
            item.get("itemId"): item
            for item in teachable_items
            if isinstance(item, dict) and isinstance(item.get("itemId"), str)
        }
        unit_by_ref = {
            unit.get("unitRef"): unit
            for unit in units
            if isinstance(unit, dict) and isinstance(unit.get("unitRef"), str)
        }

        seen_item_ids: set[str] = set()
        seen_primary_skill_ids: set[str] = set()
        changed = False
        for sequence_item in delivery_sequence:
            if not isinstance(sequence_item, dict):
                continue
            skill_ids = sequence_item.get("skillIds")
            teachable_item_id = sequence_item.get("teachableItemId")
            if not isinstance(skill_ids, list) or not skill_ids or not isinstance(teachable_item_id, str):
                continue
            primary_skill_id = skill_ids[0]
            needs_clone = (
                teachable_item_id in seen_item_ids
                or primary_skill_id in seen_primary_skill_ids
            )
            if not needs_clone:
                seen_item_ids.add(teachable_item_id)
                seen_primary_skill_ids.add(primary_skill_id)
                continue

            original_item = item_by_id.get(teachable_item_id)
            original_skill = skill_by_id.get(primary_skill_id)
            if not isinstance(original_item, dict) or not isinstance(original_skill, dict):
                continue

            position = sequence_item.get("position")
            suffix = f"session-{position}" if isinstance(position, int) else str(sequence_item.get("sequenceId") or "session")
            new_skill_id = self._unique_id(f"{primary_skill_id}-{suffix}", skill_by_id)
            new_item_id = self._unique_id(f"{teachable_item_id}-{suffix}", item_by_id)

            cloned_skill = deepcopy(original_skill)
            cloned_skill["skillId"] = new_skill_id
            cloned_skill["title"] = str(sequence_item.get("title") or original_skill.get("title") or "Session skill")
            cloned_skill["description"] = str(
                sequence_item.get("sessionFocus")
                or original_skill.get("description")
                or cloned_skill["title"]
            )
            if isinstance(sequence_item.get("contentAnchorIds"), list) and sequence_item["contentAnchorIds"]:
                cloned_skill["contentAnchorIds"] = list(sequence_item["contentAnchorIds"])
            skills.append(cloned_skill)
            skill_by_id[new_skill_id] = cloned_skill

            cloned_item = deepcopy(original_item)
            cloned_item["itemId"] = new_item_id
            cloned_item["title"] = str(sequence_item.get("title") or original_item.get("title") or "Session item")
            cloned_item["learnerOutcome"] = str(
                sequence_item.get("sessionFocus")
                or original_item.get("learnerOutcome")
                or cloned_item["title"]
            )
            cloned_item["skillIds"] = [new_skill_id]
            if isinstance(sequence_item.get("contentAnchorIds"), list) and sequence_item["contentAnchorIds"]:
                cloned_item["contentAnchorIds"] = list(sequence_item["contentAnchorIds"])
            teachable_items.append(cloned_item)
            item_by_id[new_item_id] = cloned_item

            unit = unit_by_ref.get(cloned_item.get("unitRef"))
            if isinstance(unit, dict):
                unit_skill_ids = unit.get("skillIds")
                if isinstance(unit_skill_ids, list) and new_skill_id not in unit_skill_ids:
                    unit["skillIds"] = [*unit_skill_ids, new_skill_id]

            sequence_item["teachableItemId"] = new_item_id
            sequence_item["skillIds"] = [new_skill_id]
            seen_item_ids.add(new_item_id)
            seen_primary_skill_ids.add(new_skill_id)
            changed = True

        return changed

    def _unique_id(self, preferred: str, existing: dict[str, Any]) -> str:
        candidate = preferred
        counter = 2
        while candidate in existing:
            candidate = f"{preferred}-{counter}"
            counter += 1
        return candidate

    def build_validation_retry_preview(
        self,
        *,
        payload: CurriculumGenerationRequest,
        context,
        raw_artifact,
        error,
    ) -> PromptPreview:
        raw_json = json.dumps(raw_artifact, indent=2, default=str)
        return PromptPreview(
            system_prompt=self.read_skill_markdown(),
            user_prompt="\n".join(
                [
                    self.build_user_prompt(payload, context),
                    "",
                    "The previous JSON did not validate against the curriculum artifact contract.",
                    "Return one corrected JSON object only. Preserve the intended curriculum content while fixing schema violations.",
                    "",
                    "Validation error:",
                    str(error),
                    "",
                    "Correction rules:",
                    "- `source.rationale` must be an array of strings, never one string.",
                    "- `curriculumScale`, when present, must be one of micro, week, module, course, or reference_source.",
                    "- `planningModel` must be one of content_map, session_sequence, source_sequence, single_lesson, or reference_map.",
                    "- `skills[].domainTitle`, `skills[].strandTitle`, and `skills[].goalGroupTitle` are optional; do not invent fake hierarchy just to satisfy a course-shaped template.",
                    "- Every skill must be grounded by `contentAnchorIds` or by a `teachableItems[].skillIds` reference.",
                    "- Every unit must include `skillIds` that match existing top-level `skills[].skillId` values.",
                    "- Every `teachableItems[].unitRef` must match an existing unit.",
                    "- Every `teachableItems[].skillIds` value must match an existing skill.",
                    "- Every `teachableItems[].contentAnchorIds` value must match an existing content anchor.",
                    "- Treat IDs as a closed inventory; do not reference any skillId, unitRef, anchorId, or teachableItemId that is not declared in the matching top-level array.",
                    "- If the invalid JSON references a missing ID, either declare the missing top-level object with concrete content or replace the reference with the correct existing ID.",
                    "- If planningModel is session_sequence and totalSessions is present, deliverySequence must contain exactly one item per session.",
                    "- If planningModel is session_sequence, every deliverySequence item must reference a unique teachableItemId.",
                    "- If planningModel is session_sequence, every deliverySequence item must use a unique first skillIds entry as its primary skillId.",
                    "- When a broad concept repeats across sessions, split it into session-specific review, practice, application, or project skills instead of reusing the same primary skillId.",
                    "- Every deliverySequence skillIds value must also appear in the referenced teachable item's skillIds.",
                    "- Delivery sequence positions must be contiguous and start at 1.",
                    "- If the artifact is large or the prior output was truncated, preserve the sequence while shortening strings, limiting details arrays, and removing repeated prose.",
                    "- `pacing.totalWeeks`, `pacing.sessionsPerWeek`, `pacing.sessionMinutes`, and `pacing.totalSessions` are required positive integers.",
                    "- `estimatedWeeks`, `estimatedSessions`, and delivery `estimatedMinutes` must be positive integers when present.",
                    "- Do not use `0` for any estimate. Use `1` for a very small unit or omit the estimate.",
                    "- Do not add `document`, `skillRefs`, `lessons`, `launchPlan`, or `progression`.",
                    "",
                    "Previous invalid JSON:",
                    raw_json,
                ]
            ),
        )

    def build_user_message_content(
        self,
        payload: CurriculumGenerationRequest,
        context,
        *,
        prompt_text: str | None = None,
        provider: str | None = None,
    ) -> str | list[dict]:
        prompt = prompt_text if prompt_text is not None else self.build_user_prompt(payload, context)
        source_files = payload.sourceFiles or []
        if provider != "openai" or payload.requestMode != "source_entry" or not source_files:
            return prompt
        return [{"type": "text", "text": prompt}, *build_openai_file_blocks(source_files)]
