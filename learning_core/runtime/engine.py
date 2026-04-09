from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage

from learning_core.contracts.operation import OperationEnvelope
from learning_core.contracts.responses import OperationExecuteResponse, OperationPromptPreviewResponse
from learning_core.observability.traces import ExecutionLineage, ExecutionTrace, PromptPreview
from learning_core.observability.provider_logs import write_provider_exchange_log
from learning_core.runtime.context import RuntimeContext
from learning_core.runtime.errors import ContractValidationError, ProviderExecutionError
from learning_core.runtime.providers import build_model_runtime
from learning_core.runtime.registry import SkillRegistry
from learning_core.runtime.tooling import ToolRegistry


class AgentEngine:
    def __init__(self, skill_registry: SkillRegistry, tool_registry: ToolRegistry | None = None) -> None:
        self.skill_registry = skill_registry
        self.tool_registry = tool_registry or ToolRegistry()

    def _provider_request_payload(
        self,
        *,
        context: RuntimeContext,
        skill,
        model_runtime,
        payload,
        prompt_preview: PromptPreview,
        response_mode: str,
    ) -> dict:
        return {
            "request_id": context.request_id,
            "operation_name": context.operation_name,
            "skill_name": skill.name,
            "skill_version": skill.policy.skill_version,
            "provider": model_runtime.provider,
            "provider_settings": model_runtime.provider_settings,
            "model": model_runtime.model,
            "task_kind": skill.policy.task_kind,
            "temperature": model_runtime.temperature,
            "max_tokens": model_runtime.max_tokens,
            "max_tokens_source": model_runtime.max_tokens_source,
            "response_mode": response_mode,
            "provider_request_kind": "structured_output" if response_mode == "structured" else "text_completion",
            "allowed_tools": list(skill.policy.allowed_tools),
            "provider_messages": [
                {"role": "system", "content": prompt_preview.system_prompt},
                {"role": "user", "content": prompt_preview.user_prompt},
            ],
            "input_payload": payload.model_dump(mode="json"),
            "request_envelope": OperationEnvelope(
                input=payload.model_dump(mode="json"),
                app_context=context.app_context,
                presentation_context=context.presentation_context,
                user_authored_context=context.user_authored_context,
                request_id=context.request_id,
            ).model_dump(mode="json"),
        }

    def execute(self, operation_name: str, envelope_data: dict) -> OperationExecuteResponse:
        skill = self.skill_registry.get(operation_name)
        envelope = OperationEnvelope.model_validate(envelope_data)
        context = RuntimeContext.create(
            operation_name=operation_name,
            request_id=envelope.request_id,
            app_context=envelope.app_context,
            presentation_context=envelope.presentation_context,
            user_authored_context=envelope.user_authored_context,
        )
        parsed_payload = skill.input_model.model_validate(envelope.input)
        result = skill.execute(self, parsed_payload, context)
        prompt_preview = (
            result.trace.prompt_preview
            if context.presentation_context.should_return_prompt_preview or context.app_context.debug
            else None
        )
        return OperationExecuteResponse(
            operation_name=operation_name,
            artifact=result.artifact.model_dump(),
            lineage=result.lineage,
            trace=result.trace,
            prompt_preview=prompt_preview,
        )

    def preview(self, operation_name: str, envelope_data: dict) -> OperationPromptPreviewResponse:
        skill = self.skill_registry.get(operation_name)
        envelope = OperationEnvelope.model_validate(envelope_data)
        context = RuntimeContext.create(
            operation_name=operation_name,
            request_id=envelope.request_id,
            app_context=envelope.app_context,
            presentation_context=envelope.presentation_context,
            user_authored_context=envelope.user_authored_context,
        )
        parsed_payload = skill.input_model.model_validate(envelope.input)
        preview = skill.build_prompt_preview(parsed_payload, context)
        return OperationPromptPreviewResponse(
            operation_name=operation_name,
            skill_name=skill.name,
            skill_version=skill.policy.skill_version,
            request_id=context.request_id,
            allowed_tools=list(skill.policy.allowed_tools),
            system_prompt=preview.system_prompt,
            user_prompt=preview.user_prompt,
            request_envelope=OperationEnvelope(
                input=parsed_payload.model_dump(mode="json"),
                app_context=context.app_context,
                presentation_context=context.presentation_context,
                user_authored_context=context.user_authored_context,
                request_id=context.request_id,
            ),
        )

    def run_structured_output(self, *, skill, payload, context: RuntimeContext):
        preview = skill.build_prompt_preview(payload, context)
        self.tool_registry.resolve_many(skill.policy.allowed_tools)
        model_runtime = build_model_runtime(
            task_name=context.operation_name,
            task_kind=skill.policy.task_kind,
            temperature=skill.policy.temperature,
            max_tokens=skill.policy.max_tokens,
        )
        provider_request = self._provider_request_payload(
            context=context,
            skill=skill,
            model_runtime=model_runtime,
            payload=payload,
            prompt_preview=preview,
            response_mode="structured",
        )

        try:
            structured = model_runtime.client.with_structured_output(skill.output_model)
            raw_artifact = structured.invoke(
                [
                    SystemMessage(content=preview.system_prompt),
                    HumanMessage(content=preview.user_prompt),
                ]
            )
        except Exception as error:  # pragma: no cover - provider exceptions vary
            write_provider_exchange_log(
                request=provider_request,
                response={
                    "status": "error",
                    "error_type": error.__class__.__name__,
                    "error": str(error),
                },
            )
            raise ProviderExecutionError(str(error)) from error

        try:
            artifact = skill.output_model.model_validate(raw_artifact)
        except Exception as error:
            write_provider_exchange_log(
                request=provider_request,
                response={
                    "status": "validation_error",
                    "error_type": error.__class__.__name__,
                    "error": str(error),
                    "raw_response": raw_artifact,
                },
            )
            raise ContractValidationError(str(error)) from error

        write_provider_exchange_log(
            request=provider_request,
            response={
                "status": "success",
                "raw_response": raw_artifact,
                "validated_artifact": artifact.model_dump(mode="json"),
            },
        )

        lineage = ExecutionLineage(
            operation_name=context.operation_name,
            skill_name=skill.name,
            skill_version=skill.policy.skill_version,
            provider=model_runtime.provider,
            model=model_runtime.model,
        )
        trace = ExecutionTrace(
            request_id=context.request_id,
            operation_name=context.operation_name,
            allowed_tools=list(skill.policy.allowed_tools),
            prompt_preview=preview,
            request_envelope=OperationEnvelope(
                input=payload.model_dump(mode="json"),
                app_context=context.app_context,
                presentation_context=context.presentation_context,
                user_authored_context=context.user_authored_context,
                request_id=context.request_id,
            ),
        )
        return artifact, lineage, trace

    def run_text_output(self, *, skill, payload, context: RuntimeContext) -> tuple[str, ExecutionLineage, ExecutionTrace]:
        preview = skill.build_prompt_preview(payload, context)
        self.tool_registry.resolve_many(skill.policy.allowed_tools)
        model_runtime = build_model_runtime(
            task_name=context.operation_name,
            task_kind=skill.policy.task_kind,
            temperature=skill.policy.temperature,
            max_tokens=skill.policy.max_tokens,
        )
        provider_request = self._provider_request_payload(
            context=context,
            skill=skill,
            model_runtime=model_runtime,
            payload=payload,
            prompt_preview=preview,
            response_mode="text",
        )

        try:
            response = model_runtime.client.invoke(
                [
                    SystemMessage(content=preview.system_prompt),
                    HumanMessage(content=preview.user_prompt),
                ]
            )
        except Exception as error:  # pragma: no cover - provider exceptions vary
            write_provider_exchange_log(
                request=provider_request,
                response={
                    "status": "error",
                    "error_type": error.__class__.__name__,
                    "error": str(error),
                },
            )
            raise ProviderExecutionError(str(error)) from error

        raw_text = getattr(response, "content", "")
        if isinstance(raw_text, list):
            text = "".join(
                item.get("text", "") if isinstance(item, dict) else str(item)
                for item in raw_text
            )
        else:
            text = raw_text if isinstance(raw_text, str) else str(raw_text)

        write_provider_exchange_log(
            request=provider_request,
            response={
                "status": "success",
                "raw_response": response,
                "normalized_text": text,
            },
        )

        lineage = ExecutionLineage(
            operation_name=context.operation_name,
            skill_name=skill.name,
            skill_version=skill.policy.skill_version,
            provider=model_runtime.provider,
            model=model_runtime.model,
        )
        trace = ExecutionTrace(
            request_id=context.request_id,
            operation_name=context.operation_name,
            allowed_tools=list(skill.policy.allowed_tools),
            prompt_preview=preview,
            request_envelope=OperationEnvelope(
                input=payload.model_dump(mode="json"),
                app_context=context.app_context,
                presentation_context=context.presentation_context,
                user_authored_context=context.user_authored_context,
                request_id=context.request_id,
            ),
        )
        return text, lineage, trace
