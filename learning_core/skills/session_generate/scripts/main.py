from __future__ import annotations

import json
import re

from langchain_core.messages import HumanMessage, SystemMessage

from learning_core.agent import ToolCallEvent, run_agent_loop
from learning_core.contracts.lesson_draft import (
    LESSON_BLOCK_TYPE_VALUES,
    LESSON_SHAPE_VALUES,
)
from learning_core.contracts.operation import OperationEnvelope
from learning_core.contracts.session_plan import SessionPlanArtifact, SessionPlanGenerationRequest
from learning_core.observability.provider_logs import write_provider_exchange_log
from learning_core.observability.traces import ExecutionLineage, ExecutionTrace, PromptPreview
from learning_core.runtime.errors import ContractValidationError, ProviderExecutionError
from learning_core.runtime.policy import ExecutionPolicy
from learning_core.runtime.providers import build_model_runtime
from learning_core.skills.base import StructuredOutputSkill
from learning_core.skills.prompt_utils import append_user_authored_context
from learning_core.runtime.skill import SkillExecutionResult
from learning_core.skills.session_generate.scripts.image_search import search_lesson_images

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


def _build_tool_call_log(tool_calls: list[ToolCallEvent]) -> list[dict[str, object]]:
    return [
        {
            "tool": tool_call.tool_name,
            "args": tool_call.tool_args,
            "output_preview": str(tool_call.tool_output)[:500],
        }
        for tool_call in tool_calls
    ]


def _extract_tool_names_used(tool_calls: list[ToolCallEvent]) -> set[str]:
    return {tool_call.tool_name for tool_call in tool_calls}


def _extract_json(text: str) -> str:
    match = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", text, re.DOTALL)
    if match:
        return match.group(1).strip()

    start = text.find("{")
    if start == -1:
        return text.strip()

    depth = 0
    end = start
    for index in range(start, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                end = index
                break
    return text[start : end + 1]


def _agent_text_content(response) -> str:
    content = getattr(response, "content", "")
    if isinstance(content, list):
        return "".join(
            item.get("text", "") if isinstance(item, dict) else str(item)
            for item in content
        )
    return str(content)


class SessionGenerateSkill(StructuredOutputSkill):
    name = "session_generate"
    input_model = SessionPlanGenerationRequest
    output_model = SessionPlanArtifact
    policy = ExecutionPolicy(
        skill_name="session_generate",
        skill_version="2026-04-25",
        max_tokens=8000,
        allowed_tools=("search_lesson_images",),
        max_loop_steps=6,
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
                "- Use search_lesson_images when a photo, map, diagram, artwork, or source reference would materially improve a block.",
                "- Use only exact URLs returned by search_lesson_images. Never invent, generate, guess, rewrite, or use placeholder image URLs.",
                "- If image search does not return a fitting visual, omit visual_aids and visual_aid_ids.",
                "- Use each visual aid id in at most one block. If a later block needs the same image, refer back to the earlier visual in teacher_action instead of repeating visual_aid_ids.",
                "- Prefer distinct visual aids that show meaningfully different things. Do not include multiple near-duplicate pictures just to fill the visual aid limit.",
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
                    "- Every visual_aids[].url must be copied exactly from search_lesson_images tool results.",
                    "- If image search did not return a fitting result, omit visual_aids and visual_aid_ids.",
                    "- Do not invent, generate, guess, rewrite, or use placeholder image URLs.",
                    "- Use each visual aid id in at most one block; remove repeated visual_aid_ids from later blocks.",
                    "- Keep block minutes aligned to total_minutes and keep teacher_action runnable by a non-expert adult.",
                    "",
                    "Previous invalid JSON:",
                    raw_json,
                ]
            ),
        )

    def execute(self, engine, payload: SessionPlanGenerationRequest, context) -> SkillExecutionResult:
        preview = self.build_prompt_preview(payload, context)
        model_runtime = build_model_runtime(
            task_name=context.operation_name,
            task_kind=self.policy.task_kind,
            temperature=self.policy.temperature,
            max_tokens=self.policy.max_tokens,
        )
        provider_request = engine._provider_request_payload(
            context=context,
            skill=self,
            model_runtime=model_runtime,
            payload=payload,
            provider_messages=[
                {"role": "system", "content": preview.system_prompt},
                {"role": "user", "content": preview.user_prompt},
            ],
            response_mode="agent",
        )
        tools = [search_lesson_images]
        active_tool_names = [tool.name for tool in tools]

        try:
            agent_result = run_agent_loop(
                llm=model_runtime.client,
                system_prompt=preview.system_prompt,
                user_prompt=preview.user_prompt,
                tools=tools,
                max_steps=6,
            )
        except Exception as error:
            write_provider_exchange_log(
                request=provider_request,
                response={
                    "status": "error",
                    "error_type": error.__class__.__name__,
                    "error": str(error),
                    "active_tools": active_tool_names,
                },
            )
            raise ProviderExecutionError(str(error)) from error

        raw_text = agent_result.final_text
        tool_call_log = _build_tool_call_log(agent_result.tool_calls)
        tool_names_used = _extract_tool_names_used(agent_result.tool_calls)
        json_text = _extract_json(raw_text)
        repair_attempted = False
        repair_succeeded = False
        validation_error_text = None

        try:
            artifact = self.output_model.model_validate(json.loads(json_text))
        except Exception as first_error:
            validation_error_text = str(first_error)
            repair_attempted = True
            repair_preview = self.build_validation_retry_preview(
                payload=payload,
                context=context,
                raw_artifact=json_text,
                error=first_error,
            )
            try:
                repair_response = model_runtime.client.invoke(
                    [
                        SystemMessage(content=repair_preview.system_prompt),
                        HumanMessage(content=repair_preview.user_prompt),
                    ]
                )
                repair_text = _agent_text_content(repair_response)
                repair_json = _extract_json(repair_text)
                artifact = self.output_model.model_validate(json.loads(repair_json))
                repair_succeeded = True
                raw_text = repair_text
                json_text = repair_json
            except Exception as repair_error:
                write_provider_exchange_log(
                    request=provider_request,
                    response={
                        "status": "validation_error",
                        "initial_error": validation_error_text,
                        "repair_error": str(repair_error),
                        "raw_agent_response": agent_result.final_text,
                        "tool_calls": tool_call_log,
                        "active_tools": active_tool_names,
                    },
                )
                raise ContractValidationError(
                    f"Validation failed after repair. Initial: {validation_error_text}. Repair: {repair_error}"
                ) from repair_error

        visual_urls = [visual_aid.url for visual_aid in artifact.visual_aids]
        if visual_urls and "search_lesson_images" not in tool_names_used:
            validation_error = ContractValidationError(
                "Lesson visual aids require search_lesson_images tool usage."
            )
            write_provider_exchange_log(
                request=provider_request,
                response={
                    "status": "semantic_validation_error",
                    "error": str(validation_error),
                    "visual_urls": visual_urls,
                    "raw_agent_response": raw_text,
                    "tool_calls": tool_call_log,
                    "active_tools": active_tool_names,
                },
            )
            raise validation_error

        write_provider_exchange_log(
            request=provider_request,
            response={
                "status": "success",
                "raw_agent_response": raw_text,
                "validated_artifact": artifact.model_dump(mode="json", exclude_none=True),
                "tool_calls": tool_call_log,
                "active_tools": active_tool_names,
                "repair_attempted": repair_attempted,
                "repair_succeeded": repair_succeeded,
                "validation_error": validation_error_text,
            },
        )

        lineage = ExecutionLineage(
            operation_name=context.operation_name,
            skill_name=self.name,
            skill_version=self.policy.skill_version,
            provider=model_runtime.provider,
            model=model_runtime.model,
        )
        trace = ExecutionTrace(
            request_id=context.request_id,
            operation_name=context.operation_name,
            allowed_tools=list(self.policy.allowed_tools),
            prompt_preview=preview,
            request_envelope=OperationEnvelope(
                input=payload.model_dump(mode="json"),
                app_context=context.app_context,
                presentation_context=context.presentation_context,
                user_authored_context=context.user_authored_context,
                request_id=context.request_id,
            ),
            agent_trace={
                "tool_calls": tool_call_log,
                "active_tools": active_tool_names,
                "visual_urls": visual_urls,
                "repair_attempted": repair_attempted,
                "repair_succeeded": repair_succeeded,
                "validation_error": validation_error_text,
            },
        )
        return SkillExecutionResult(
            artifact=artifact,
            lineage=lineage,
            trace=trace,
        )
