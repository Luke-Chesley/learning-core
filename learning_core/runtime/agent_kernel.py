from __future__ import annotations

from learning_core.response_types import get_response_type
from learning_core.runtime.finalization import KernelExecutionResult
from learning_core.runtime.pack_resolution import resolve_runtime_packs
from learning_core.runtime.preview import KernelPreview
from learning_core.runtime.request_normalization import RuntimeRequest
from learning_core.runtime.tool_runtime import resolve_tool_runtime_plan
from learning_core.workflow_cards.registry import get_workflow_card


class AgentKernel:
    def preview(self, runtime_request: RuntimeRequest, *, skill) -> KernelPreview:
        workflow_card = get_workflow_card(runtime_request.workflow_card)
        selected_packs = resolve_runtime_packs(runtime_request)
        tool_plan = resolve_tool_runtime_plan(runtime_request, skill.policy)
        prompt_preview = workflow_card.build_prompt_preview(
            runtime_request.payload,
            runtime_request.runtime_context,
            runtime_request,
            selected_packs,
        )
        return KernelPreview(
            prompt_preview=prompt_preview,
            task_profile=runtime_request.task_profile,
            response_type=runtime_request.requested_response_type,
            workflow_card=runtime_request.workflow_card,
            runtime_mode=runtime_request.operation_definition.execution_strategy,
            selected_packs=[pack.name for pack in selected_packs],
            tool_families=list(tool_plan.tool_families),
            allowed_tools=list(tool_plan.allowed_tool_names),
        )

    def execute(self, runtime_request: RuntimeRequest, *, skill, engine) -> KernelExecutionResult:
        preview = self.preview(runtime_request, skill=skill)
        strategy = runtime_request.operation_definition.execution_strategy
        if strategy == "structured":
            artifact, lineage, trace = engine.run_structured_output(
                skill=skill,
                payload=runtime_request.payload,
                context=runtime_request.runtime_context,
            )
            trace.task_profile = preview.task_profile
            trace.response_type = preview.response_type
            trace.workflow_card = preview.workflow_card
            trace.runtime_mode = preview.runtime_mode
            trace.selected_packs = preview.selected_packs
            trace.tool_families = preview.tool_families
            return KernelExecutionResult(artifact=artifact, lineage=lineage, trace=trace)

        if strategy == "text":
            response_type = get_response_type(runtime_request.requested_response_type)
            raw_text, lineage, trace = engine.run_text_output(
                skill=skill,
                payload=runtime_request.payload,
                context=runtime_request.runtime_context,
            )
            artifact = response_type.build_text_artifact(raw_text)
            trace.task_profile = preview.task_profile
            trace.response_type = preview.response_type
            trace.workflow_card = preview.workflow_card
            trace.runtime_mode = preview.runtime_mode
            trace.selected_packs = preview.selected_packs
            trace.tool_families = preview.tool_families
            return KernelExecutionResult(artifact=artifact, lineage=lineage, trace=trace)

        result = skill.execute(engine, runtime_request.payload, runtime_request.runtime_context)
        result.trace.task_profile = preview.task_profile
        result.trace.response_type = preview.response_type
        result.trace.workflow_card = preview.workflow_card
        result.trace.runtime_mode = preview.runtime_mode
        result.trace.selected_packs = preview.selected_packs
        result.trace.tool_families = preview.tool_families
        return KernelExecutionResult(
            artifact=result.artifact,
            lineage=result.lineage,
            trace=result.trace,
        )
