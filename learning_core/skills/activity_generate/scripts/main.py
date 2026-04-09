from __future__ import annotations

import json
import re
from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage

from learning_core.agent import run_agent_loop
from learning_core.contracts.operation import OperationEnvelope
from learning_core.observability.provider_logs import write_provider_exchange_log
from learning_core.observability.traces import ExecutionLineage, ExecutionTrace, PromptPreview
from learning_core.runtime.context import RuntimeContext
from learning_core.runtime.errors import ContractValidationError, ProviderExecutionError
from learning_core.runtime.providers import build_model_runtime
from learning_core.runtime.skill import SkillDefinition, SkillExecutionResult
from learning_core.skills.activity_generate.scripts.policy import ACTIVITY_GENERATE_POLICY
from learning_core.skills.activity_generate.scripts.schemas import ActivityArtifact, ActivityGenerationInput
from learning_core.skills.activity_generate.scripts.tooling import read_ui_component

_SKILL_DIR = Path(__file__).resolve().parent.parent
_REGISTRY_INDEX_PATH = _SKILL_DIR / "ui_registry_index.md"


def _read_skill_markdown() -> str:
    return (_SKILL_DIR / "SKILL.md").read_text(encoding="utf-8").strip()


def _read_registry_index() -> str:
    return _REGISTRY_INDEX_PATH.read_text(encoding="utf-8").strip()


def _build_user_prompt(payload: ActivityGenerationInput, context: RuntimeContext) -> str:
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

    # Append the registry index so the model can see available components.
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(_read_registry_index())

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(
        "Generate a single ActivitySpec JSON object. "
        "You may call `read_ui_component` to read full docs for components you are considering (typically 0-2). "
        "Your final output must be exactly one JSON object — no text outside the JSON."
    )

    return "\n".join(lines)


def _extract_json(text: str) -> str:
    """Extract JSON from text that may include markdown fences or surrounding prose."""
    # Try to find a JSON code block first.
    match = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", text, re.DOTALL)
    if match:
        return match.group(1).strip()

    # Fall back to finding the outermost { ... } pair.
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
        return _build_user_prompt(payload, context)

    def build_prompt_preview(self, payload, context) -> PromptPreview:
        return PromptPreview(
            system_prompt=_read_skill_markdown(),
            user_prompt=self.build_user_prompt(payload, context),
        )

    def execute(self, engine, payload: ActivityGenerationInput, context: RuntimeContext) -> SkillExecutionResult:
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
            prompt_preview=preview,
            response_mode="agent",
        )

        # --- Run the ReAct agent loop ---
        try:
            agent_result = run_agent_loop(
                llm=model_runtime.client,
                system_prompt=preview.system_prompt,
                user_prompt=preview.user_prompt,
                tools=[read_ui_component],
                max_steps=5,
            )
        except Exception as error:
            write_provider_exchange_log(
                request=provider_request,
                response={
                    "status": "error",
                    "error_type": error.__class__.__name__,
                    "error": str(error),
                },
            )
            raise ProviderExecutionError(str(error)) from error

        raw_text = agent_result.final_text
        tool_call_log = [
            {"tool": tc.tool_name, "args": tc.tool_args, "output_length": len(tc.tool_output)}
            for tc in agent_result.tool_calls
        ]

        # --- Parse and validate ---
        json_text = _extract_json(raw_text)
        repair_attempted = False
        repair_succeeded = False
        validation_error_text = None

        try:
            parsed = json.loads(json_text)
            artifact = ActivityArtifact.model_validate(parsed)
        except Exception as first_error:
            validation_error_text = str(first_error)
            repair_attempted = True

            # --- One repair pass ---
            try:
                repair_prompt = (
                    "The JSON you produced failed validation.\n\n"
                    f"Error: {validation_error_text}\n\n"
                    f"Invalid JSON:\n```json\n{json_text}\n```\n\n"
                    "Return only the corrected JSON object. No text outside the JSON."
                )
                repair_response = model_runtime.client.invoke(
                    [
                        SystemMessage(content=preview.system_prompt),
                        HumanMessage(content=repair_prompt),
                    ]
                )
                repair_text = getattr(repair_response, "content", "")
                if isinstance(repair_text, list):
                    repair_text = "".join(
                        item.get("text", "") if isinstance(item, dict) else str(item)
                        for item in repair_text
                    )
                repair_json = _extract_json(str(repair_text))
                repaired = json.loads(repair_json)
                artifact = ActivityArtifact.model_validate(repaired)
                repair_succeeded = True
                raw_text = str(repair_text)
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
                    },
                )
                raise ContractValidationError(
                    f"Validation failed after repair. Initial: {validation_error_text}. Repair: {repair_error}"
                ) from repair_error

        # --- Log and return ---
        write_provider_exchange_log(
            request=provider_request,
            response={
                "status": "success",
                "raw_agent_response": agent_result.final_text,
                "validated_artifact": artifact.model_dump(mode="json", exclude_none=True),
                "tool_calls": tool_call_log,
                "repair_attempted": repair_attempted,
                "repair_succeeded": repair_succeeded,
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
                "component_docs_read": [tc.tool_args.get("path", "") for tc in agent_result.tool_calls],
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
