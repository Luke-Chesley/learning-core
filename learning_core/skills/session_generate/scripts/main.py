from __future__ import annotations

import json
import re

from learning_core.contracts.lesson_draft import (
    LESSON_BLOCK_TYPE_VALUES,
    LESSON_SHAPE_VALUES,
    validate_lesson_visual_aid_url,
)
from learning_core.contracts.session_plan import SessionPlanArtifact, SessionPlanGenerationRequest
from learning_core.observability.traces import PromptPreview
from learning_core.runtime.policy import ExecutionPolicy
from learning_core.skills.base import StructuredOutputSkill
from learning_core.skills.prompt_utils import append_user_authored_context

_EXACT_SCRIPT_PATTERNS = (
    re.compile(r"\bexact(?:ly)? what to say\b", re.IGNORECASE),
    re.compile(r"\bexact script\b", re.IGNORECASE),
    re.compile(r"\bscript(?:ed)?\b", re.IGNORECASE),
    re.compile(r"\bread (?:it|this) aloud\b", re.IGNORECASE),
    re.compile(r"\bverbatim\b", re.IGNORECASE),
    re.compile(r"\bcalm\b", re.IGNORECASE),
    re.compile(r"\blimited branching\b", re.IGNORECASE),
)

_PARTIAL_SOURCE_PATTERNS = (
    re.compile(r"\bpartial\b", re.IGNORECASE),
    re.compile(r"\bmissing\b", re.IGNORECASE),
    re.compile(r"\bexcerpt\b", re.IGNORECASE),
    re.compile(r"\bcropped\b", re.IGNORECASE),
    re.compile(r"\bcut off\b", re.IGNORECASE),
    re.compile(r"\bdo not invent\b", re.IGNORECASE),
)

_MULTI_LEARNER_PATTERNS = (
    re.compile(r"\btwo learners\b", re.IGNORECASE),
    re.compile(r"\bboth kids\b", re.IGNORECASE),
    re.compile(r"\bolder\b", re.IGNORECASE),
    re.compile(r"\byounger\b", re.IGNORECASE),
    re.compile(r"\b8-year-old\b", re.IGNORECASE),
    re.compile(r"\b9-year-old\b", re.IGNORECASE),
    re.compile(r"\b11-year-old\b", re.IGNORECASE),
    re.compile(r"\b13-year-old\b", re.IGNORECASE),
    re.compile(r"\bage split\b", re.IGNORECASE),
    re.compile(r"\bdifferent depth\b", re.IGNORECASE),
)


def _request_signal_text(payload: SessionPlanGenerationRequest, context) -> str:
    values: list[str] = [payload.topic or "", payload.title or ""]
    values.extend(payload.objectives)
    values.extend(item.title for item in payload.routeItems)
    values.extend(item.objective for item in payload.routeItems)

    authored = context.user_authored_context
    values.extend(
        [
            authored.parent_goal or "",
            authored.note or "",
            authored.teacher_note or "",
            authored.custom_instruction or "",
            *authored.special_constraints,
            *authored.avoidances,
        ]
    )

    return "\n".join(value for value in values if value).strip()


def _matches_any(text: str, patterns: tuple[re.Pattern[str], ...]) -> bool:
    return any(pattern.search(text) for pattern in patterns)


def _infer_total_minutes(payload: SessionPlanGenerationRequest, context) -> int:
    if payload.resolvedTiming:
        return payload.resolvedTiming.resolvedTotalMinutes

    request_text = _request_signal_text(payload, context)
    route_minutes = sum(
        item.estimatedMinutes for item in payload.routeItems if isinstance(item.estimatedMinutes, int)
    )

    if _matches_any(request_text, _EXACT_SCRIPT_PATTERNS):
        return min(route_minutes, 20) if route_minutes > 0 else 15

    if _matches_any(request_text, _PARTIAL_SOURCE_PATTERNS):
        return min(route_minutes, 25) if route_minutes > 0 else 20

    if route_minutes > 0:
        return max(10, min(route_minutes, 35))

    return 30


def _visual_aid_candidates(payload: SessionPlanGenerationRequest) -> list[dict[str, object]]:
    if not payload.context:
        return []

    candidates = payload.context.get("visualAidCandidates")
    if not isinstance(candidates, list):
        return []

    normalized: list[dict[str, object]] = []
    seen_urls: set[str] = set()
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        url = candidate.get("url")
        title = candidate.get("title")
        if not isinstance(url, str) or not url.strip():
            continue
        try:
            validate_lesson_visual_aid_url(url)
        except ValueError:
            continue
        if url in seen_urls:
            continue
        seen_urls.add(url)
        normalized.append(
            {
                "id": candidate.get("id") if isinstance(candidate.get("id"), str) else f"visual-{len(normalized) + 1}",
                "title": title if isinstance(title, str) and title.strip() else "Visual aid",
                "url": url,
                "sourceName": candidate.get("sourceName") if isinstance(candidate.get("sourceName"), str) else None,
            }
        )
    return normalized[:6]


class SessionGenerateSkill(StructuredOutputSkill):
    name = "session_generate"
    input_model = SessionPlanGenerationRequest
    output_model = SessionPlanArtifact
    policy = ExecutionPolicy(
        skill_name="session_generate",
        skill_version="2026-04-20",
        max_tokens=8000,
    )

    def build_user_prompt(self, payload: SessionPlanGenerationRequest, context) -> str:
        request_text = _request_signal_text(payload, context)
        exact_script_request = _matches_any(request_text, _EXACT_SCRIPT_PATTERNS)
        partial_source_request = _matches_any(request_text, _PARTIAL_SOURCE_PATTERNS)
        multi_learner_request = _matches_any(request_text, _MULTI_LEARNER_PATTERNS)
        objectives = (
            "\n".join(f"{index + 1}. {objective}" for index, objective in enumerate(payload.objectives))
            if payload.objectives
            else "1. Use the current day's items to keep the lesson coherent."
        )
        route_items = (
            "\n".join(
                [
                    f"{index + 1}. {item.title} ({item.subject}, {item.estimatedMinutes} min)\n"
                    f"   Objective: {item.objective}\n"
                    f"   Route label: {item.lessonLabel}"
                    + (f"\n   Note: {item.note}" if item.note else "")
                    for index, item in enumerate(payload.routeItems)
                ]
            )
            if payload.routeItems
            else "No route items provided."
        )
        materials = " · ".join(payload.materials) if payload.materials else "None listed."
        week_summary = "None provided."

        if payload.context and isinstance(payload.context.get("weeklyPlanningSnapshot"), dict):
            weekly_snapshot = payload.context["weeklyPlanningSnapshot"]
            days = weekly_snapshot.get("days") if isinstance(weekly_snapshot.get("days"), list) else []
            if days:
                week_summary = "\n".join(
                    f"{index + 1}. {day.get('label', 'Day')}: "
                    f"{', '.join(day.get('itemTitles', [])) if isinstance(day.get('itemTitles'), list) and day.get('itemTitles') else 'No scheduled items'}"
                    for index, day in enumerate(days)
                    if isinstance(day, dict)
                )

        learner_name = None
        if payload.context and isinstance(payload.context.get("learnerName"), str):
            learner_name = payload.context["learnerName"]
        elif context.app_context.learner_id:
            learner_name = context.app_context.learner_id

        total_minutes = _infer_total_minutes(payload, context)
        visual_aid_candidates = _visual_aid_candidates(payload)

        lines = [
            f"Generate a structured lesson plan for {learner_name or 'the learner'} on "
            f"{payload.context.get('dailyWorkspaceSnapshot', {}).get('date', 'today') if payload.context else 'today'}.",
            "",
            f"Curriculum source: {payload.title or payload.topic}",
            f"Week context: {payload.context.get('weeklyPlanningSnapshot', {}).get('weekLabel', 'Current week') if payload.context else 'Current week'}",
            f"Route items: {len(payload.routeItems)}",
            f"Total time: {total_minutes} minutes",
            f"Objectives in scope: {len(payload.objectives)}",
            f"Allowed lesson_shape slugs: {', '.join(LESSON_SHAPE_VALUES)}",
            f"Allowed blocks[].type values: {', '.join(LESSON_BLOCK_TYPE_VALUES)}",
        ]

        lines.extend(
            [
                "",
                "Session sizing rules:",
                f"- Keep the lesson genuinely teachable within about {total_minutes} minutes.",
                "- Do not inflate a bounded request into a generic 45-minute lesson unless the source clearly requires it.",
                "- Prefer fewer, clearer blocks over filler transitions or repeated review.",
                "- Keep top-level lesson_shape separate from block types.",
                "- Never use a lesson_shape slug as blocks[].type. For a practice-heavy lesson, set top-level lesson_shape to practice_heavy and use block types like guided_practice or independent_practice.",
                "- Use visual_aids only when seeing the image materially improves teaching, such as clouds, maps, diagrams, artwork, or source images.",
                "- Include at most 3 visual aids.",
                "- Use only exact URLs from the allowed visual-aid candidate list below. Never invent, generate, guess, rewrite, or use placeholder image URLs.",
                "- If no allowed visual-aid candidate fits the lesson, omit visual_aids and visual_aid_ids.",
                "",
                "Teacher guidance rules:",
                "- Assume the adult may be capable but not topic-expert unless the request clearly says otherwise.",
                "- teacher_action must be concrete enough that a non-expert adult could run the block without outside prep.",
                "- When a block depends on specialized vocabulary or a domain-specific move, briefly define or model it inside teacher_action on first use.",
                "- learner_action should describe what the learner actually says, points to, writes, builds, or practices.",
                "- check_for should tell the adult what to hear, see, or collect as evidence.",
            ]
        )

        if exact_script_request:
            lines.extend(
                [
                    "- This is a script-first request. The parent should be able to read the core prompts almost verbatim.",
                    "- Keep teacher_action lines speakable, concise, and low-branching.",
                    "- Favor 2 to 4 compact blocks and avoid broad open-ended questioning.",
                ]
            )

        if partial_source_request:
            lines.extend(
                [
                    "- The source is partial or messy. Keep uncertainty explicit and do not invent missing pages or hidden context.",
                    "- Stay bounded to what the source can honestly support today plus only a light next-step hint if needed.",
                ]
            )

        if multi_learner_request:
            lines.extend(
                [
                    "- Preserve distinct expectations for the learners instead of collapsing into one shared task.",
                    "- Make the split visible inside block actions, adaptations, or teacher notes so the parent can run it without guessing.",
                ]
            )

        if visual_aid_candidates:
            lines.extend(
                [
                    "",
                    "Allowed visual-aid candidates:",
                    *[
                        f"{index + 1}. id: {candidate['id']}; title: {candidate['title']}; url: {candidate['url']}"
                        + (f"; source: {candidate['sourceName']}" if candidate.get("sourceName") else "")
                        for index, candidate in enumerate(visual_aid_candidates)
                    ],
                ]
            )
        else:
            lines.extend(
                [
                    "",
                    "Allowed visual-aid candidates: none. Omit visual_aids and visual_aid_ids.",
                ]
            )

        if payload.lessonShape:
            lines.append(
                "Lesson shape preference (canonical lesson_shape slug; reuse exactly if included): "
                f"{payload.lessonShape}"
            )

        if payload.teacherContext:
            if payload.teacherContext.subject_comfort:
                lines.append(f"Teacher subject comfort: {payload.teacherContext.subject_comfort}")
            if payload.teacherContext.prep_tolerance:
                lines.append(f"Prep tolerance: {payload.teacherContext.prep_tolerance}")
            if payload.teacherContext.teaching_style:
                lines.append(f"Teaching style: {payload.teacherContext.teaching_style}")
            if payload.teacherContext.role:
                lines.append(f"Role: {payload.teacherContext.role}")

        append_user_authored_context(lines, context)
        lines.extend(
            [
                "",
                "Objectives:",
                objectives,
                "",
                "Route items:",
                route_items,
                "",
                "Materials available:",
                materials,
                "",
                "Weekly schedule:",
                week_summary,
                "",
                "Additional app context:",
                payload.context and __import__("json").dumps(payload.context, indent=2) or "No additional context provided.",
                "",
                "Return only valid JSON. No other text.",
            ]
        )
        return "\n".join(lines)

    def build_validation_retry_preview(
        self,
        *,
        payload: SessionPlanGenerationRequest,
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
                    "The previous JSON did not validate against the structured lesson draft contract.",
                    "Return one corrected JSON object only. Preserve the lesson content while fixing schema violations.",
                    "",
                    "Validation error:",
                    str(error),
                    "",
                    "Correction rules:",
                    f"- Every blocks[].type must be one of: {', '.join(LESSON_BLOCK_TYPE_VALUES)}.",
                    f"- Top-level lesson_shape, when present, must be one of: {', '.join(LESSON_SHAPE_VALUES)}.",
                    "- Never put lesson_shape slugs such as practice_heavy, balanced, or project_based in blocks[].type.",
                    "- If the intended lesson shape is practice-heavy, keep lesson_shape as practice_heavy and use guided_practice or independent_practice blocks.",
                    "- Every visual_aids[].url must be copied exactly from the allowed visual-aid candidate list.",
                    "- If there are no allowed visual-aid candidates, omit visual_aids and visual_aid_ids.",
                    "- Do not invent, generate, guess, rewrite, or use placeholder image URLs.",
                    "- Keep block minutes aligned to total_minutes and keep teacher_action runnable by a non-expert adult.",
                    "",
                    "Previous invalid JSON:",
                    raw_json,
                ]
            ),
        )
