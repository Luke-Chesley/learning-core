from __future__ import annotations

from learning_core.contracts.lesson_draft import LESSON_SHAPE_VALUES
from learning_core.contracts.session_plan import SessionPlanArtifact, SessionPlanGenerationRequest
from learning_core.runtime.policy import ExecutionPolicy
from learning_core.skills.base import StructuredOutputSkill
from learning_core.skills.prompt_utils import append_user_authored_context


class SessionGenerateSkill(StructuredOutputSkill):
    name = "session_generate"
    input_model = SessionPlanGenerationRequest
    output_model = SessionPlanArtifact
    policy = ExecutionPolicy(
        skill_name="session_generate",
        skill_version="2026-04-09",
        max_tokens=8000,
    )

    def build_user_prompt(self, payload: SessionPlanGenerationRequest, context) -> str:
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

        total_minutes = (
            payload.resolvedTiming.resolvedTotalMinutes
            if payload.resolvedTiming
            else 45
        )

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
        ]

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
