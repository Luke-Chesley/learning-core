from __future__ import annotations

import json

from learning_core.observability.traces import PromptPreview
from learning_core.contracts.curriculum import (
    CurriculumRevisionRequest,
    CurriculumRevisionTurn,
    iter_document_skill_entries,
)
from learning_core.runtime.policy import ExecutionPolicy
from learning_core.runtime.skill import SkillExecutionResult
from learning_core.skills.base import StructuredOutputSkill
from learning_core.skills.prompt_utils import append_user_authored_context, format_curriculum_transcript


class CurriculumReviseSkill(StructuredOutputSkill):
    name = "curriculum_revise"
    input_model = CurriculumRevisionRequest
    output_model = CurriculumRevisionTurn
    policy = ExecutionPolicy(
        skill_name="curriculum_revise",
        skill_version="2026-04-22",
        max_tokens=12000,
    )

    def build_user_prompt(self, payload: CurriculumRevisionRequest, context) -> str:
        lines = [
            f"Active learner: {payload.learnerName}",
            "",
            "Current curriculum snapshot:",
            payload.currentCurriculum and __import__("json").dumps(payload.currentCurriculum, indent=2) or "{}",
        ]

        if payload.currentRequest:
            lines.extend(["", "Latest parent request:", payload.currentRequest])

        lines.extend(
            [
                "",
                "Revision conversation transcript:",
                format_curriculum_transcript(payload.messages),
                "",
                "Revision instructions:",
                "- Read the snapshot and transcript directly.",
                "- Decide whether the change is a split, rename, targeted adjust, or broader rewrite.",
                "- Preserve unchanged branches unless the parent explicitly asked for a broader rewrite.",
                "- Preserve domain -> strand -> goal group labels when they are meaningful in the existing curriculum.",
                "- Do not force course-shaped hierarchy onto short curricula; skillId plus title is enough for tiny or week-sized scopes.",
                "- Preserve concrete teachable granularity while keeping the hierarchy coherent.",
                "- Preserve or revise contentAnchors, teachableItems, deliverySequence, and projectArc so the curriculum still owns what to teach.",
                "- Units should remain coarse curriculum groupings, not lesson plans.",
                "- Return one flat skills list plus units that reference those skills by skillId.",
                "- Every skill must be grounded in contentAnchorIds or teachableItems.",
                "- If planningModel is session_sequence, deliverySequence must contain one item per session.",
                "- Preserve or emit pacing.totalWeeks, pacing.sessionsPerWeek, pacing.sessionMinutes, and pacing.totalSessions as positive integers.",
                "- Return the full revised curriculum artifact when action is \"apply\".",
                "- If the request is too vague to apply safely, ask one precise clarification question.",
            ]
        )

        if payload.correctionNotes:
            lines.extend(
                [
                    "",
                    "Retry correction notes:",
                    *[f"{index + 1}. {note}" for index, note in enumerate(payload.correctionNotes)],
                ]
            )

        append_user_authored_context(lines, context)
        lines.extend(["", "Respond with either one clarification question or the full revised curriculum artifact."])
        return "\n".join(lines)

    def execute(self, engine, payload: CurriculumRevisionRequest, context) -> SkillExecutionResult[CurriculumRevisionTurn]:
        turn, lineage, trace = engine.run_structured_output(
            skill=self,
            payload=payload,
            context=context,
        )
        return SkillExecutionResult(
            artifact=turn,
            lineage=lineage,
            trace=trace,
        )

    def repair_invalid_artifact(self, *, raw_artifact, payload, context, error):
        del payload, context, error
        if not isinstance(raw_artifact, dict):
            return None

        repaired = dict(raw_artifact)
        artifact = repaired.get("artifact")
        if repaired.get("action") != "apply" or not isinstance(artifact, dict):
            return None

        expected_artifact_keys = {
            "source",
            "intakeSummary",
            "pacing",
            "curriculumScale",
            "planningModel",
            "skills",
            "units",
            "contentAnchors",
            "teachableItems",
            "deliverySequence",
            "projectArc",
            "sourceCoverage",
            "document",
        }
        document = artifact.get("document")
        if document is not None and not isinstance(document, dict):
            return None

        moved_any = False
        repaired_artifact = dict(artifact)
        repaired_document = dict(document or {})

        for key, value in list(repaired_artifact.items()):
            if key in expected_artifact_keys:
                continue
            if not isinstance(value, (dict, list, str)):
                continue
            if key in repaired_document:
                continue
            repaired_document[key] = value
            repaired_artifact.pop(key, None)
            moved_any = True

        if repaired_document:
            skills = []
            skill_id_by_ref = {}
            skill_ids_by_title = {}
            for ordinal, (skill_ref, path, title) in enumerate(iter_document_skill_entries(repaired_document), start=1):
                domain_title = path[0] if len(path) > 0 else "General"
                strand_title = path[1] if len(path) > 1 else "General"
                goal_group_title = " / ".join(path[2:-1]) if len(path) > 3 else (path[2] if len(path) > 2 else "Skills")
                skill_id = f"skill-{ordinal}"
                skill_id_by_ref[skill_ref] = skill_id
                skill_ids_by_title.setdefault(title, []).append(skill_id)
                skills.append(
                    {
                        "skillId": skill_id,
                        "domainTitle": domain_title,
                        "strandTitle": strand_title,
                        "goalGroupTitle": goal_group_title,
                        "title": title,
                        "description": title,
                        "contentAnchorIds": [f"anchor-{ordinal}"],
                        "practiceCue": f"Practice {title}.",
                        "assessmentCue": f"Look for visible evidence of {title}.",
                    }
                )

            repaired_units = []
            for raw_unit in repaired_artifact.get("units", []):
                if not isinstance(raw_unit, dict):
                    return None
                unit = dict(raw_unit)
                if "skillIds" not in unit:
                    if isinstance(unit.get("skillRefs"), list):
                        unit["skillIds"] = [
                            skill_id_by_ref[skill_ref]
                            for skill_ref in unit["skillRefs"]
                            if isinstance(skill_ref, str) and skill_ref in skill_id_by_ref
                        ]
                    elif isinstance(unit.get("skills"), list):
                        resolved_skill_ids = []
                        for title in unit["skills"]:
                            if not isinstance(title, str):
                                continue
                            matches = skill_ids_by_title.get(title, [])
                            if len(matches) != 1:
                                return None
                            resolved_skill_ids.append(matches[0])
                        unit["skillIds"] = resolved_skill_ids
                unit.pop("skillRefs", None)
                unit.pop("skills", None)
                unit.pop("skillTitles", None)
                repaired_units.append(unit)

            content_anchors = [
                {
                    "anchorId": f"anchor-{index}",
                    "title": skill["title"],
                    "summary": skill.get("description") or skill["title"],
                    "details": [],
                    "sourceRefs": [{"label": "Revision document repair"}],
                    "grounding": "source_grounded",
                }
                for index, skill in enumerate(skills, start=1)
            ]
            first_unit_ref = repaired_units[0].get("unitRef") if repaired_units else "unit:1:revised"
            unit_ref_by_skill_id = {}
            for unit in repaired_units:
                unit_skill_ids = unit.get("skillIds", [])
                if not isinstance(unit_skill_ids, list):
                    continue
                for skill_id in unit_skill_ids:
                    if isinstance(skill_id, str):
                        unit_ref_by_skill_id[skill_id] = unit.get("unitRef", first_unit_ref)
            teachable_items = [
                {
                    "itemId": f"item-{index}",
                    "unitRef": unit_ref_by_skill_id.get(skill["skillId"], first_unit_ref),
                    "title": skill["title"],
                    "focusQuestion": f"What should the learner understand or do for {skill['title']}?",
                    "contentAnchorIds": skill["contentAnchorIds"],
                    "namedAnchors": [skill["title"]],
                    "vocabulary": [],
                    "learnerOutcome": skill.get("description") or skill["title"],
                    "assessmentCue": skill.get("assessmentCue") or skill["title"],
                    "misconceptions": [],
                    "parentNotes": [],
                    "skillIds": [skill["skillId"]],
                    "estimatedSessions": 1,
                    "sourceRefs": [{"label": "Revision document repair"}],
                }
                for index, skill in enumerate(skills, start=1)
            ]
            pacing = dict(repaired_artifact.get("pacing") or {})
            total_sessions = max(1, len(skills))
            pacing.setdefault("totalWeeks", 1)
            pacing.setdefault("sessionsPerWeek", total_sessions)
            pacing.setdefault("sessionMinutes", 30)
            pacing.setdefault("totalSessions", total_sessions)
            pacing.setdefault("coverageStrategy", "Preserve repaired curriculum scope.")
            pacing.setdefault("coverageNotes", ["Pacing was inferred while repairing a legacy revision artifact."])

            repaired_artifact = {
                "source": repaired_artifact.get("source"),
                "intakeSummary": repaired_artifact.get("intakeSummary"),
                "pacing": pacing,
                "curriculumScale": repaired_artifact.get("curriculumScale"),
                "planningModel": repaired_artifact.get("planningModel") or "content_map",
                "skills": skills,
                "units": repaired_units,
                "contentAnchors": content_anchors,
                "teachableItems": teachable_items,
                "deliverySequence": [],
                "sourceCoverage": [],
            }
            repaired["artifact"] = repaired_artifact
            return repaired

        if not moved_any:
            return None

        repaired["artifact"] = repaired_artifact
        return repaired

    def build_validation_retry_preview(
        self,
        *,
        payload,
        context,
        raw_artifact,
        error,
    ) -> PromptPreview | None:
        system_prompt = "\n\n".join(
            [
                self.read_skill_markdown(),
                "Repair instructions:",
                "- The previous response was invalid.",
                "- Return only one corrected JSON object.",
                "- The top-level shape must be exactly assistantMessage, action, changeSummary, and optional artifact.",
                "- When action is apply, artifact must contain source, intakeSummary, pacing, curriculumScale, planningModel, skills, units, contentAnchors, and teachableItems.",
                "- Every skill belongs in artifact.skills with skillId, title, description, contentAnchorIds, practiceCue, and assessmentCue; domainTitle, strandTitle, and goalGroupTitle are optional.",
                "- Units may reference those skills only through units[].skillIds.",
                "- Teachable items must reference existing unitRef, skillIds, and contentAnchorIds.",
                "- If planningModel is session_sequence and pacing.totalSessions is present, deliverySequence must have one item per session.",
                "- artifact.pacing.totalWeeks, sessionsPerWeek, sessionMinutes, and totalSessions are required positive integers.",
                "- Preserve the intended curriculum content while fixing the JSON structure.",
            ]
        )
        user_prompt = "\n".join(
            [
                self.build_user_prompt(payload, context),
                "",
                "Previous invalid JSON:",
                json.dumps(raw_artifact, indent=2, ensure_ascii=True),
                "",
                f"Validation error: {error}",
                "",
                "Repair the JSON so it matches the exact schema. Return only the corrected JSON object.",
            ]
        )
        return PromptPreview(system_prompt=system_prompt, user_prompt=user_prompt)
