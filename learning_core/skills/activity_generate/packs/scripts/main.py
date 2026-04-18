from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from learning_core.agent import ToolCallEvent, run_agent_loop
from learning_core.contracts.operation import OperationEnvelope
from learning_core.observability.provider_logs import write_provider_exchange_log
from learning_core.observability.traces import ExecutionLineage, ExecutionTrace, PromptPreview
from learning_core.runtime.context import RuntimeContext
from learning_core.runtime.errors import ContractValidationError, ProviderExecutionError
from learning_core.runtime.providers import build_model_runtime
from learning_core.runtime.skill import SkillDefinition, SkillExecutionResult
from learning_core.skills.activity_generate.packs import ALL_PACKS, Pack
from learning_core.skills.activity_generate.packs.base import PackPlanningResult, PackValidationContext
from learning_core.skills.activity_generate.packs.scripts.policy import ACTIVITY_GENERATE_POLICY
from learning_core.skills.activity_generate.packs.scripts.schemas import ActivityArtifact, ActivityGenerationInput
from learning_core.skills.activity_generate.packs.scripts.tooling import read_ui_spec
from learning_core.skills.activity_generate.validation.widgets import normalize_and_validate_widget_activity

_SKILL_DIR = Path(__file__).resolve().parent.parent
_REGISTRY_INDEX_PATH = _SKILL_DIR / "ui_registry_index.md"
_PACKS_DIR = _SKILL_DIR / "packs"
_PACK_INDEX_PATH = _PACKS_DIR / "index.md"
_TOOL_OUTPUT_PREVIEW_CHARS = 320

_PACKS_BY_NAME: dict[str, Pack] = {pack.name: pack for pack in ALL_PACKS}


@dataclass(frozen=True)
class PackSelection:
    included_packs: tuple[str, ...]
    pack_selection_reason: dict[str, list[str]]
    subject_inference: dict[str, Any]


def _read_skill_markdown() -> str:
    return (_SKILL_DIR / "SKILL.md").read_text(encoding="utf-8").strip()


def _read_registry_index() -> str:
    return _REGISTRY_INDEX_PATH.read_text(encoding="utf-8").strip()


def _read_pack_index() -> str:
    return _PACK_INDEX_PATH.read_text(encoding="utf-8").strip()


def _read_ui_spec_file(path: str) -> str:
    return (_SKILL_DIR / path).read_text(encoding="utf-8").strip()


def _contains_keyword(text: str, keyword: str) -> bool:
    normalized_keyword = keyword.strip().lower()
    if not normalized_keyword:
        return False
    if " " in normalized_keyword:
        return normalized_keyword in text
    return re.search(rf"(?<![a-z]){re.escape(normalized_keyword)}(?![a-z])", text) is not None


def _dedupe_preserve_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for value in values:
        if value not in seen:
            deduped.append(value)
            seen.add(value)
    return deduped


def _select_packs(payload: ActivityGenerationInput) -> PackSelection:
    lesson = payload.lesson_draft
    sources = {
        "subject": (payload.subject or "").strip(),
        "lesson_title": lesson.title.strip(),
        "lesson_focus": lesson.lesson_focus.strip(),
        "linked_skill_titles": " ".join(payload.linked_skill_titles).strip(),
    }
    lowered_sources = {key: value.lower() for key, value in sources.items() if value}

    matched_keywords: dict[str, dict[str, list[str]]] = {}
    pack_selection_reason: dict[str, list[str]] = {}
    included_packs: list[str] = []

    for pack in ALL_PACKS:
        pack_matches: dict[str, list[str]] = {}
        pack_reasons: list[str] = []

        for source_name, source_value in lowered_sources.items():
            hits = [keyword for keyword in pack.keywords if _contains_keyword(source_value, keyword)]
            if not hits:
                continue
            deduped_hits = _dedupe_preserve_order(hits)
            pack_matches[source_name] = deduped_hits
            label = source_name.replace("_", " ")
            pack_reasons.append(f"{label} matched: {', '.join(deduped_hits)}")

        matched_keywords[pack.name] = pack_matches
        pack_selection_reason[pack.name] = pack_reasons
        if pack_reasons:
            included_packs.append(pack.name)

    subject_inference = {
        "provided_subject": payload.subject,
        "lesson_title": lesson.title,
        "lesson_focus": lesson.lesson_focus,
        "linked_skill_titles": list(payload.linked_skill_titles),
        "matched_keywords": matched_keywords,
    }

    return PackSelection(
        included_packs=tuple(included_packs),
        pack_selection_reason=pack_selection_reason,
        subject_inference=subject_inference,
    )


def _collect_auto_injected_ui_specs(pack_selection: PackSelection) -> list[str]:
    specs: list[str] = []
    seen: set[str] = set()
    for pack_name in pack_selection.included_packs:
        for spec_path in _PACKS_BY_NAME[pack_name].auto_injected_ui_specs():
            if spec_path not in seen:
                specs.append(spec_path)
                seen.add(spec_path)
    return specs


def _build_user_prompt(
    payload: ActivityGenerationInput,
    context: RuntimeContext,
    pack_selection: PackSelection,
    planning_results: dict[str, PackPlanningResult] | None = None,
) -> str:
    lesson = payload.lesson_draft
    lines: list[str] = []

    lines.append("## Activity generation request")
    lines.append("")
    learner_line = f"Learner: {payload.learner_name}"
    if payload.learner_grade_level:
        learner_line += f" ({payload.learner_grade_level})"
    lines.append(learner_line)
    lines.append(f"Subject: {payload.subject or 'General'}")
    lines.append(f"Session budget: {lesson.total_minutes} minutes")

    if payload.workflow_mode:
        lines.append(f"Workflow mode: {payload.workflow_mode}")
    elif context.app_context.workflow_mode:
        lines.append(f"Workflow mode: {context.app_context.workflow_mode}")

    lines.append("")
    lines.append("## Lesson plan")
    lines.append(f"Title: {lesson.title}")
    lines.append(f"Focus: {lesson.lesson_focus}")

    if lesson.primary_objectives:
        lines.append("Objectives:")
        for objective in lesson.primary_objectives:
            lines.append(f"- {objective}")

    if lesson.success_criteria:
        lines.append("Success criteria (use these as mastery indicators in teacherSupport):")
        for criterion in lesson.success_criteria:
            lines.append(f"- {criterion}")

    if lesson.blocks:
        lines.append("Lesson blocks:")
        for block in lesson.blocks:
            optional = " [optional]" if block.optional else ""
            lines.append(f"  [{block.type}{optional}] {block.title} ({block.minutes} min)")
            lines.append(f"    Purpose: {block.purpose}")
            lines.append(f"    Learner: {block.learner_action}")

    if lesson.materials:
        lines.append(f"Materials: {', '.join(lesson.materials)}")

    if lesson.teacher_notes:
        lines.append("Teacher notes:")
        for note in lesson.teacher_notes:
            lines.append(f"- {note}")

    if lesson.adaptations:
        lines.append("Adaptations:")
        for adaptation in lesson.adaptations:
            lines.append(f"- {adaptation.trigger}: {adaptation.action}")

    if lesson.assessment_artifact:
        lines.append(f"Assessment artifact: {lesson.assessment_artifact}")

    if lesson.lesson_shape:
        lines.append(f"Lesson shape: {lesson.lesson_shape}")

    lines.append("")
    lines.append(f'Activity scope: session - "{lesson.title}"')

    if payload.linked_objective_ids:
        lines.append("")
        lines.append("Linked objective IDs (use these in linkedObjectiveIds field):")
        lines.append(", ".join(payload.linked_objective_ids))

    if payload.linked_skill_titles:
        lines.append("")
        lines.append("Linked skill titles (use these in linkedSkillTitles field):")
        lines.append(", ".join(payload.linked_skill_titles))

    if payload.standard_ids:
        lines.append("")
        lines.append("Standard IDs in scope:")
        lines.append(", ".join(payload.standard_ids))

    if context.user_authored_context.parent_goal:
        lines.append("")
        lines.append(f"Parent goal: {context.user_authored_context.parent_goal}")

    if context.user_authored_context.note:
        lines.append("")
        lines.append(f"Parent note: {context.user_authored_context.note}")

    if context.user_authored_context.teacher_note:
        lines.append("")
        lines.append(f"Teacher note: {context.user_authored_context.teacher_note}")

    if context.user_authored_context.special_constraints:
        lines.append("")
        lines.append("Special constraints:")
        for value in context.user_authored_context.special_constraints:
            lines.append(f"- {value}")

    if context.user_authored_context.avoidances:
        lines.append("")
        lines.append("Avoid:")
        for value in context.user_authored_context.avoidances:
            lines.append(f"- {value}")

    if context.user_authored_context.custom_instruction:
        lines.append("")
        lines.append(f"Custom instruction: {context.user_authored_context.custom_instruction}")

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(_read_registry_index())

    if pack_selection.included_packs:
        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append(_read_pack_index())

        for pack_name in pack_selection.included_packs:
            pack = _PACKS_BY_NAME[pack_name]
            lines.append("")
            lines.append("---")
            lines.append("")
            for section in pack.prompt_sections():
                lines.append(section)
                lines.append("")
            if lines[-1] == "":
                lines.pop()

    # Auto-inject key UI/widget spec docs for active packs
    auto_injected_specs = _collect_auto_injected_ui_specs(pack_selection)
    if auto_injected_specs:
        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append("## Auto-included widget specifications")
        lines.append("")
        lines.append("The following widget/component specs are included automatically because an active subject pack uses them. You do not need to read these via tools.")
        for spec_path in auto_injected_specs:
            lines.append("")
            lines.append(f"### {spec_path}")
            lines.append("")
            lines.append(_read_ui_spec_file(spec_path))

    if planning_results:
        planning_sections = [
            section
            for result in planning_results.values()
            for section in result.prompt_sections
            if section.strip()
        ]
        if planning_sections:
            lines.append("")
            lines.append("---")
            lines.append("")
            lines.append("## Pre-built pack planning context")
            lines.append("")
            lines.append(
                "Some active packs have already planned and validated domain examples before final composition. "
                "Treat those examples as fixed inputs."
            )
            for section in planning_sections:
                lines.append("")
                lines.append(section)

    lines.append("")
    lines.append("---")
    lines.append("")
    generation_instruction = (
        "Generate a single ActivitySpec JSON object. "
        "You already have the base UI registry, and relevant subject packs may also be included. "
        "Active subject packs may already include core widget docs above. "
        "If a rich interactive surface is needed, consider `interactive_widget`. "
        "Read UI specs with `read_ui_spec` only when that materially helps you choose or configure a component or widget well. "
        "Many requests need no doc reads. Specialized requests may justify a few. "
        "If you emit a pack-specific widget (e.g. a chess board), validate it with the pack's domain tools before finalizing. "
        "Do not make factual claims about a domain state (e.g. check, checkmate, side to move) that you have not validated with a domain tool. "
        "Use good taste when selecting components. Prefer a coherent, pedagogically strong activity over a crowded one. "
        "Prefer the smallest set of components that creates a strong activity. "
        "Use as many components as the activity genuinely needs and no more. "
        "Do not use components or widgets just because they exist. "
        "Escalate to interactive widgets only when they materially improve the learning interaction. "
    )
    if planning_results:
        generation_instruction += (
            "When pre-built pack examples are provided, compose the activity around those validated examples. "
            "Preserve the provided example ids and validated engine-backed fields exactly. "
            "Do not invent new raw domain states or mutate validated engine facts unless the planning context explicitly allows it. "
        )
    generation_instruction += (
        "Your final output must be exactly one JSON object matching the strict ActivityArtifact contract. "
        "Do not include any text outside the JSON."
    )
    lines.append(generation_instruction)

    return "\n".join(lines)


def _build_prompt_preview(
    payload: ActivityGenerationInput,
    context: RuntimeContext,
    planning_results: dict[str, PackPlanningResult] | None = None,
) -> tuple[PromptPreview, PackSelection]:
    pack_selection = _select_packs(payload)
    preview = PromptPreview(
        system_prompt=_read_skill_markdown(),
        user_prompt=_build_user_prompt(payload, context, pack_selection, planning_results),
    )
    return preview, pack_selection


def _build_tool_call_log(tool_calls: list[ToolCallEvent]) -> list[dict[str, Any]]:
    log: list[dict[str, Any]] = []
    for tool_call in tool_calls:
        output_text = str(tool_call.tool_output)
        log.append(
            {
                "tool": tool_call.tool_name,
                "args": tool_call.tool_args,
                "output_length": len(output_text),
                "output_preview": output_text[:_TOOL_OUTPUT_PREVIEW_CHARS],
                "output_hash": hashlib.sha256(output_text.encode("utf-8")).hexdigest()[:16],
            }
        )
    return log


def _extract_ui_specs_read(tool_calls: list[ToolCallEvent]) -> list[str]:
    specs_read: list[str] = []
    for tool_call in tool_calls:
        if tool_call.tool_name != "read_ui_spec":
            continue
        path = tool_call.tool_args.get("path")
        if isinstance(path, str) and path not in specs_read:
            specs_read.append(path)
    return specs_read


def _extract_tool_names_used(tool_calls: list[ToolCallEvent]) -> set[str]:
    return {tool_call.tool_name for tool_call in tool_calls}


def _build_active_tools(pack_selection: PackSelection) -> list[Any]:
    tools: list[Any] = [read_ui_spec]
    for pack_name in pack_selection.included_packs:
        tools.extend(_PACKS_BY_NAME[pack_name].tools())
    return tools


def _run_agent_loop_with_adaptive_retry(
    *,
    llm,
    system_prompt: str,
    user_prompt: str,
    tools: list[Any],
    initial_max_steps: int = 5,
    fallback_max_steps: int = 8,
):
    try:
        return run_agent_loop(
            llm=llm,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            tools=tools,
            max_steps=initial_max_steps,
        )
    except Exception as error:
        if "GRAPH_RECURSION_LIMIT" not in str(error):
            raise
        return run_agent_loop(
            llm=llm,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            tools=tools,
            max_steps=fallback_max_steps,
        )


def _get_active_packs(pack_selection: PackSelection) -> list[Pack]:
    return [_PACKS_BY_NAME[name] for name in pack_selection.included_packs]


def _run_pack_planning_phases(
    *,
    payload: ActivityGenerationInput,
    context: RuntimeContext,
    active_packs: list[Pack],
    model_runtime,
) -> dict[str, PackPlanningResult]:
    planning_results: dict[str, PackPlanningResult] = {}
    for pack in active_packs:
        if not pack.needs_planning(payload, context):
            continue
        result = pack.run_planning_phase(payload, context, model_runtime)
        if result is not None:
            planning_results[pack.name] = result
    return planning_results


def _check_pack_tool_usage(
    artifact: ActivityArtifact,
    pack_selection: PackSelection,
    tool_names_used: set[str],
    planning_results: dict[str, PackPlanningResult] | None = None,
) -> list[tuple[Pack, list[str]]]:
    """Check if pack-specific widgets were generated without required pack tool usage.

    Returns list of (pack, widget_component_ids) for packs needing repair.
    """
    missing: list[tuple[Pack, list[str]]] = []
    for pack_name in pack_selection.included_packs:
        if planning_results and pack_name in planning_results:
            continue
        pack = _PACKS_BY_NAME[pack_name]
        pack_widget_ids = pack.detect_pack_widgets(artifact)
        if not pack_widget_ids:
            continue
        required_tools = pack.required_tool_names()
        if not required_tools:
            continue
        if not tool_names_used.intersection(required_tools):
            missing.append((pack, pack_widget_ids))
    return missing


def _extract_json(text: str) -> str:
    """Extract JSON from text that may include markdown fences or surrounding prose."""
    match = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", text, re.DOTALL)
    if match:
        return match.group(1).strip()

    start = text.find("{")
    if start == -1:
        return text.strip()

    depth = 0
    end = start
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                end = i
                break
    return text[start : end + 1]


class ActivityGenerateSkill(SkillDefinition):
    name = "activity_generate"
    input_model = ActivityGenerationInput
    output_model = ActivityArtifact
    policy = ACTIVITY_GENERATE_POLICY

    def build_user_prompt(self, payload: ActivityGenerationInput, context: RuntimeContext) -> str:
        pack_selection = _select_packs(payload)
        return _build_user_prompt(payload, context, pack_selection)

    def build_prompt_preview(self, payload, context) -> PromptPreview:
        preview, _ = _build_prompt_preview(payload, context)
        return preview

    def execute(self, engine, payload: ActivityGenerationInput, context: RuntimeContext) -> SkillExecutionResult:
        pack_selection = _select_packs(payload)
        active_packs = _get_active_packs(pack_selection)
        auto_injected_specs = _collect_auto_injected_ui_specs(pack_selection)

        model_runtime = build_model_runtime(
            task_name=context.operation_name,
            task_kind=self.policy.task_kind,
            temperature=self.policy.temperature,
            max_tokens=self.policy.max_tokens,
        )

        try:
            planning_results = _run_pack_planning_phases(
                payload=payload,
                context=context,
                active_packs=active_packs,
                model_runtime=model_runtime,
            )
        except Exception as error:
            write_provider_exchange_log(
                request={
                    "request_id": context.request_id,
                    "operation_name": context.operation_name,
                    "status": "pack_planning_error",
                    "included_packs": list(pack_selection.included_packs),
                    "pack_selection_reason": pack_selection.pack_selection_reason,
                    "subject_inference": pack_selection.subject_inference,
                },
                response={
                    "status": "pack_planning_error",
                    "error_type": error.__class__.__name__,
                    "error": str(error),
                },
            )
            raise ProviderExecutionError(str(error)) from error

        preview = PromptPreview(
            system_prompt=_read_skill_markdown(),
            user_prompt=_build_user_prompt(payload, context, pack_selection, planning_results),
        )

        provider_messages = [
            {"role": "system", "content": preview.system_prompt},
            {"role": "user", "content": preview.user_prompt},
        ]
        provider_request = engine._provider_request_payload(
            context=context,
            skill=self,
            model_runtime=model_runtime,
            payload=payload,
            provider_messages=provider_messages,
            response_mode="agent",
        )

        tools = _build_active_tools(pack_selection)
        active_tool_names = [tool.name for tool in tools]

        try:
            agent_result = _run_agent_loop_with_adaptive_retry(
                llm=model_runtime.client,
                system_prompt=preview.system_prompt,
                user_prompt=preview.user_prompt,
                tools=tools,
                initial_max_steps=5,
                fallback_max_steps=8,
            )
        except Exception as error:
            write_provider_exchange_log(
                request=provider_request,
                response={
                    "status": "error",
                    "error_type": error.__class__.__name__,
                    "error": str(error),
                    "pack_planning_results": {
                        name: result.structured_data for name, result in planning_results.items()
                    },
                    "included_packs": list(pack_selection.included_packs),
                    "pack_selection_reason": pack_selection.pack_selection_reason,
                    "subject_inference": pack_selection.subject_inference,
                },
            )
            raise ProviderExecutionError(str(error)) from error

        raw_text = agent_result.final_text
        tool_call_log = _build_tool_call_log(agent_result.tool_calls)
        ui_specs_read = _extract_ui_specs_read(agent_result.tool_calls)
        tool_names_used = _extract_tool_names_used(agent_result.tool_calls)

        json_text = _extract_json(raw_text)
        repair_attempted = False
        repair_succeeded = False
        pack_tool_repair_triggered = False
        validation_error_text = None
        semantic_validation_hard_errors: list[str] = []
        semantic_validation_soft_warnings: list[str] = []

        try:
            parsed = json.loads(json_text)
            artifact = ActivityArtifact.model_validate(parsed)
        except Exception as first_error:
            validation_error_text = str(first_error)
            repair_attempted = True

            try:
                repair_prompt = (
                    "The JSON you produced failed validation.\n\n"
                    f"Error: {validation_error_text}\n\n"
                    f"Invalid JSON:\n```json\n{json_text}\n```\n\n"
                    "Make the smallest set of corrections needed to satisfy the contract. "
                    "Keep IDs, overall composition, and intent stable unless the contract failure makes that impossible.\n\n"
                    "Return only the corrected JSON object. No text outside the JSON."
                )
                repair_result = _run_agent_loop_with_adaptive_retry(
                    llm=model_runtime.client,
                    system_prompt=preview.system_prompt,
                    user_prompt=repair_prompt,
                    tools=tools,
                    initial_max_steps=4,
                    fallback_max_steps=7,
                )
                repair_json = _extract_json(repair_result.final_text)
                repaired = json.loads(repair_json)
                artifact = ActivityArtifact.model_validate(repaired)
                repair_tool_log = _build_tool_call_log(repair_result.tool_calls)
                tool_call_log.extend(repair_tool_log)
                tool_names_used.update(_extract_tool_names_used(repair_result.tool_calls))
                repair_succeeded = True
                raw_text = repair_result.final_text
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
                        "ui_specs_read": ui_specs_read,
                        "included_packs": list(pack_selection.included_packs),
                        "pack_selection_reason": pack_selection.pack_selection_reason,
                        "subject_inference": pack_selection.subject_inference,
                    },
                )
                raise ContractValidationError(
                    f"Validation failed after repair. Initial: {validation_error_text}. Repair: {repair_error}"
                ) from repair_error

        # Check if pack-specific widgets were emitted without required tool usage
        missing_pack_tool_usage = _check_pack_tool_usage(
            artifact,
            pack_selection,
            tool_names_used,
            planning_results,
        )
        if missing_pack_tool_usage:
            pack_tool_repair_triggered = True
            repair_attempted = True
            repair_lines = [
                "The JSON you produced contains pack-specific widgets that were not validated with the available domain tools.\n"
            ]
            for pack, widget_ids in missing_pack_tool_usage:
                guidance = pack.repair_guidance()
                if guidance:
                    repair_lines.append(f"Pack '{pack.name}' (widgets: {', '.join(widget_ids)}): {guidance}")
            repair_lines.append(f"\nCurrent JSON:\n```json\n{artifact.model_dump_json(indent=2)}\n```\n")
            repair_lines.append(
                "Validate each pack-specific widget using the appropriate domain tools, "
                "fix any issues found, and return the corrected JSON. No text outside the JSON."
            )

            try:
                repair_result = _run_agent_loop_with_adaptive_retry(
                    llm=model_runtime.client,
                    system_prompt=preview.system_prompt,
                    user_prompt="\n".join(repair_lines),
                    tools=tools,
                    initial_max_steps=5,
                    fallback_max_steps=8,
                )
                repair_json = _extract_json(repair_result.final_text)
                repaired = json.loads(repair_json)
                artifact = ActivityArtifact.model_validate(repaired)

                # Merge repair tool calls into the log
                repair_tool_log = _build_tool_call_log(repair_result.tool_calls)
                tool_call_log.extend(repair_tool_log)
                tool_names_used.update(_extract_tool_names_used(repair_result.tool_calls))
                repair_succeeded = True
                raw_text = repair_result.final_text
                json_text = repair_json
            except Exception as repair_error:
                write_provider_exchange_log(
                    request=provider_request,
                    response={
                        "status": "pack_tool_repair_error",
                        "repair_error": str(repair_error),
                        "missing_pack_tools": [
                            {"pack": pack.name, "widgets": ids} for pack, ids in missing_pack_tool_usage
                        ],
                        "raw_agent_response": agent_result.final_text,
                        "tool_calls": tool_call_log,
                        "ui_specs_read": ui_specs_read,
                        "active_tools": active_tool_names,
                        "included_packs": list(pack_selection.included_packs),
                        "pack_selection_reason": pack_selection.pack_selection_reason,
                        "subject_inference": pack_selection.subject_inference,
                    },
                )
                # Don't hard fail on pack tool repair failure — continue with semantic validation
                pass

        # Run semantic validation (base + pack validators)
        validation_contexts = {
            pack_name: PackValidationContext(planning_result=result)
            for pack_name, result in planning_results.items()
        }
        artifact, hard_errors, soft_warnings = normalize_and_validate_widget_activity(
            artifact,
            active_packs,
            validation_contexts,
        )
        semantic_validation_hard_errors = list(hard_errors)
        semantic_validation_soft_warnings = list(soft_warnings)

        # Repair only if hard errors exist — soft warnings alone are acceptable
        if hard_errors:
            repair_attempted = True
            try:
                issue_lines = []
                if hard_errors:
                    issue_lines.append("Hard validation errors (must fix):")
                    issue_lines.extend(f"- {error}" for error in hard_errors)
                if soft_warnings:
                    issue_lines.append("Soft warnings (fix if possible, but not required):")
                    issue_lines.extend(f"- {warning}" for warning in soft_warnings)

                planning_context_lines: list[str] = []
                if planning_results:
                    for result in planning_results.values():
                        for section in result.prompt_sections:
                            if section.strip():
                                planning_context_lines.append(section)

                repair_prompt = (
                    "The JSON you produced passed schema validation but has semantic issues.\n\n"
                    + "\n".join(issue_lines)
                )
                if planning_context_lines:
                    repair_prompt += (
                        "\n\n## Validated planning context\n\n"
                        "The following validated examples were provided during generation. "
                        "All validated examples MUST appear in the final activity with their original "
                        "componentId, widget.state, widget.interaction, and widget.evaluation preserved exactly.\n\n"
                        + "\n\n".join(planning_context_lines)
                    )
                repair_prompt += (
                    "\n\nCurrent JSON:\n```json\n"
                    + artifact.model_dump_json(indent=2)
                    + "\n```\n\n"
                    "Make the smallest set of corrections needed to resolve the hard errors. "
                    "Fix soft warnings where possible without disrupting the activity. "
                    "Do not add arbitrary new components or fields. Keep IDs, structure, and lesson intent stable unless a listed failure requires a change.\n\n"
                    "Return only the corrected JSON object. No text outside the JSON."
                )
                repair_result = _run_agent_loop_with_adaptive_retry(
                    llm=model_runtime.client,
                    system_prompt=preview.system_prompt,
                    user_prompt=repair_prompt,
                    tools=tools,
                    initial_max_steps=5,
                    fallback_max_steps=8,
                )
                repair_json = _extract_json(repair_result.final_text)
                repaired = json.loads(repair_json)
                artifact = ActivityArtifact.model_validate(repaired)
                repair_tool_log = _build_tool_call_log(repair_result.tool_calls)
                tool_call_log.extend(repair_tool_log)
                tool_names_used.update(_extract_tool_names_used(repair_result.tool_calls))
                artifact, hard_errors, soft_warnings = normalize_and_validate_widget_activity(
                    artifact,
                    active_packs,
                    validation_contexts,
                )
                if hard_errors:
                    raise ContractValidationError("; ".join(hard_errors))
                # Soft warnings after repair are acceptable
                repair_succeeded = True
                raw_text = repair_result.final_text
                json_text = repair_json
            except Exception as repair_error:
                write_provider_exchange_log(
                    request=provider_request,
                    response={
                        "status": "semantic_validation_error",
                        "hard_errors": semantic_validation_hard_errors,
                        "soft_warnings": semantic_validation_soft_warnings,
                        "repair_error": str(repair_error),
                        "raw_agent_response": agent_result.final_text,
                        "tool_calls": tool_call_log,
                        "ui_specs_read": ui_specs_read,
                        "active_tools": active_tool_names,
                        "included_packs": list(pack_selection.included_packs),
                        "pack_selection_reason": pack_selection.pack_selection_reason,
                        "subject_inference": pack_selection.subject_inference,
                    },
                )
                raise ContractValidationError(
                    f"Semantic validation failed after repair: {repair_error}"
                ) from repair_error

        # Build pack validation results for trace
        pack_validation_results: dict[str, Any] = {}
        for pack in active_packs:
            pack_widget_ids = pack.detect_pack_widgets(artifact)
            required_tools = pack.required_tool_names()
            used_required = tool_names_used.intersection(required_tools) if required_tools else set()
            planning_applied = pack.name in planning_results
            pack_validation_results[pack.name] = {
                "widget_ids": pack_widget_ids,
                "required_tools": required_tools,
                "tools_used": sorted(used_required),
                "planning_applied": planning_applied,
                "tool_use_satisfied": True
                if planning_applied
                else bool(used_required) if pack_widget_ids and required_tools else True,
            }

        write_provider_exchange_log(
            request=provider_request,
            response={
                "status": "success",
                "raw_agent_response": agent_result.final_text,
                "validated_artifact": artifact.model_dump(mode="json", exclude_none=True),
                "tool_calls": tool_call_log,
                "ui_specs_read": ui_specs_read,
                "active_tools": active_tool_names,
                "repair_attempted": repair_attempted,
                "repair_succeeded": repair_succeeded,
                "pack_tool_repair_triggered": pack_tool_repair_triggered,
                "semantic_validation_hard_errors": semantic_validation_hard_errors,
                "semantic_validation_soft_warnings": semantic_validation_soft_warnings,
                "included_packs": list(pack_selection.included_packs),
                "pack_planning_results": {
                    name: result.structured_data for name, result in planning_results.items()
                },
                "pack_selection_reason": pack_selection.pack_selection_reason,
                "subject_inference": pack_selection.subject_inference,
                "pack_validation_results": pack_validation_results,
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
                "ui_specs_read": ui_specs_read,
                "auto_injected_ui_specs": auto_injected_specs,
                "active_tools": active_tool_names,
                "included_packs": list(pack_selection.included_packs),
                "pack_planning_results": {
                    name: result.structured_data for name, result in planning_results.items()
                },
                "pack_selection_reason": pack_selection.pack_selection_reason,
                "subject_inference": pack_selection.subject_inference,
                "repair_attempted": repair_attempted,
                "repair_succeeded": repair_succeeded,
                "pack_tool_repair_triggered": pack_tool_repair_triggered,
                "validation_error": validation_error_text,
                "semantic_validation_hard_errors": semantic_validation_hard_errors,
                "semantic_validation_soft_warnings": semantic_validation_soft_warnings,
                "pack_validation_results": pack_validation_results,
            },
        )

        return SkillExecutionResult(
            artifact=artifact,
            lineage=lineage,
            trace=trace,
        )
