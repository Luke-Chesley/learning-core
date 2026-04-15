from __future__ import annotations

from typing import Any

from learning_core.contracts.operation import OperationEnvelope
from learning_core.observability.traces import ExecutionTrace
from learning_core.runtime.preview import KernelPreview
from learning_core.runtime.request_normalization import RuntimeRequest


def build_execution_trace(
    runtime_request: RuntimeRequest,
    preview: KernelPreview,
    *,
    agent_trace: dict[str, Any] | None = None,
) -> ExecutionTrace:
    return ExecutionTrace(
        request_id=runtime_request.request_id,
        operation_name=runtime_request.operation_name,
        allowed_tools=preview.allowed_tools,
        prompt_preview=preview.prompt_preview,
        request_envelope=OperationEnvelope(
            input=runtime_request.raw_payload,
            app_context=runtime_request.app_context,
            presentation_context=runtime_request.presentation_context,
            user_authored_context=runtime_request.user_authored_context,
            request_id=runtime_request.request_id,
        ),
        task_profile=preview.task_profile,
        response_type=preview.response_type,
        workflow_card=preview.workflow_card,
        runtime_mode=preview.runtime_mode,
        selected_packs=preview.selected_packs,
        tool_families=preview.tool_families,
        agent_trace=agent_trace,
    )
