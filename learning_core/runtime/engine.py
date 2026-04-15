from __future__ import annotations

import json
import os
import re
import time

from langchain_core.messages import HumanMessage, SystemMessage

from learning_core.contracts.operation import OperationEnvelope
from learning_core.contracts.responses import OperationExecuteResponse, OperationPromptPreviewResponse
from learning_core.observability.traces import ExecutionLineage, ExecutionTrace, PromptPreview
from learning_core.observability.provider_logs import write_provider_exchange_log
from learning_core.runtime.agent_kernel import AgentKernel
from learning_core.runtime.context import RuntimeContext
from learning_core.runtime.errors import ContractValidationError, ProviderExecutionError
from learning_core.runtime.providers import build_model_runtime
from learning_core.runtime.request_normalization import normalize_runtime_request
from learning_core.runtime.registry import SkillRegistry
from learning_core.runtime.tooling import ToolRegistry


class AgentEngine:
    def __init__(self, skill_registry: SkillRegistry, tool_registry: ToolRegistry | None = None) -> None:
        self.skill_registry = skill_registry
        self.tool_registry = tool_registry or ToolRegistry()
        self.kernel = AgentKernel()

    def _provider_request_payload(
        self,
        *,
        context: RuntimeContext,
        skill,
        model_runtime,
        payload,
        prompt_preview: PromptPreview,
        response_mode: str,
        structured_output_method: str | None = None,
    ) -> dict:
        provider_request_kind = "text_completion"
        if response_mode == "structured":
            provider_request_kind = (
                f"structured_output_{structured_output_method}"
                if structured_output_method
                else "structured_output"
            )
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
            "provider_request_kind": provider_request_kind,
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

    def _structured_output_method_for_provider(self, provider: str) -> str | None:
        # GPT-5.4-mini is currently more reliable with JSON mode than with
        # LangChain's explicit function-calling / json-schema steering.
        if provider == "openai":
            return "json_mode"
        return None

    def _is_retryable_provider_error(self, provider: str, error: Exception) -> bool:
        if provider != "openai":
            return False
        message = str(error).lower()
        return (
            "error code: 500" in message
            or "server_error" in message
            or "upstream connect error" in message
            or "disconnect/reset before headers" in message
        )

    def _invoke_provider_with_retry(self, provider: str, fn, *, max_attempts: int = 3):
        last_error: Exception | None = None
        for attempt in range(1, max_attempts + 1):
            try:
                return fn()
            except Exception as error:  # pragma: no cover - provider exceptions vary
                last_error = error
                if attempt >= max_attempts or not self._is_retryable_provider_error(provider, error):
                    raise
                time.sleep(0.4 * attempt)

        if last_error is not None:
            raise last_error
        raise RuntimeError("Provider invocation failed without an error.")

    def _extract_json(self, text: str) -> str:
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

    def _run_text_json_fallback(self, *, skill, payload, context, structured_error: Exception):
        raw_text, lineage, trace = self.run_text_output(
            skill=skill,
            payload=payload,
            context=context,
        )
        extracted_json = self._extract_json(raw_text)

        try:
            raw_artifact = json.loads(extracted_json)
        except Exception as error:
            raise ContractValidationError(
                "Structured-output fallback returned invalid JSON: "
                f"{error}. Raw text: {raw_text[:400]}"
            ) from error

        try:
            artifact = skill.output_model.model_validate(raw_artifact)
        except Exception as error:
            raise ContractValidationError(
                f"Structured-output fallback returned an invalid artifact: {error}"
            ) from error

        trace.agent_trace = {
            **(trace.agent_trace or {}),
            "structured_output_fallback": {
                "strategy": "text_json",
                "reason": structured_error.__class__.__name__,
                "message": str(structured_error),
            },
        }

        return artifact, lineage, trace

    def _kernel_enabled_for_operation(self, operation_name: str) -> bool:
        env_name = f"LEARNING_CORE_USE_KERNEL_FOR_{operation_name.upper()}"
        raw_value = os.getenv(env_name)
        if raw_value is None:
            return True
        return raw_value.strip().lower() not in {"0", "false", "no", "off"}

    def _execute_legacy(self, operation_name: str, envelope_data: dict) -> OperationExecuteResponse:
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
            artifact=result.artifact.model_dump(mode="json", exclude_none=True),
            lineage=result.lineage,
            trace=result.trace,
            prompt_preview=prompt_preview,
        )

    def _preview_legacy(self, operation_name: str, envelope_data: dict) -> OperationPromptPreviewResponse:
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

    def execute(self, operation_name: str, envelope_data: dict) -> OperationExecuteResponse:
        if not self._kernel_enabled_for_operation(operation_name):
            return self._execute_legacy(operation_name, envelope_data)
        skill = self.skill_registry.get(operation_name)
        runtime_request = normalize_runtime_request(operation_name, envelope_data, skill.input_model)
        result = self.kernel.execute(runtime_request, skill=skill, engine=self)
        prompt_preview = (
            result.trace.prompt_preview
            if runtime_request.presentation_context.should_return_prompt_preview or runtime_request.app_context.debug
            else None
        )
        return OperationExecuteResponse(
            operation_name=operation_name,
            artifact=result.artifact.model_dump(mode="json", exclude_none=True),
            lineage=result.lineage,
            trace=result.trace,
            prompt_preview=prompt_preview,
        )

    def preview(self, operation_name: str, envelope_data: dict) -> OperationPromptPreviewResponse:
        if not self._kernel_enabled_for_operation(operation_name):
            return self._preview_legacy(operation_name, envelope_data)
        skill = self.skill_registry.get(operation_name)
        runtime_request = normalize_runtime_request(operation_name, envelope_data, skill.input_model)
        preview = self.kernel.preview(runtime_request, skill=skill)
        return OperationPromptPreviewResponse(
            operation_name=operation_name,
            skill_name=skill.name,
            skill_version=skill.policy.skill_version,
            request_id=runtime_request.request_id,
            allowed_tools=preview.allowed_tools,
            system_prompt=preview.prompt_preview.system_prompt,
            user_prompt=preview.prompt_preview.user_prompt,
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
        )

    def execute_runtime_request_by_name(self, operation_name: str, envelope_data: dict) -> OperationExecuteResponse:
        return self.execute(operation_name, envelope_data)

    def execute_generate_from_source(self, envelope_data: dict) -> OperationExecuteResponse:
        envelope = OperationEnvelope.model_validate(envelope_data)
        source_request = envelope.input
        source_result = self.execute("source_interpret", envelope_data)
        interpretation = source_result.artifact
        routed_route = (
            "weekly_plan"
            if interpretation["recommendedHorizon"] in {"next_few_days", "current_week", "starter_week"}
            else "single_lesson"
        )
        bounded_plan_result = self.execute(
            "bounded_plan_generate",
            {
                "input": {
                    "learnerName": source_request.get("learnerName") or envelope.app_context.learner_id or "Learner",
                    "requestedRoute": source_request.get("requestedRoute", routed_route),
                    "routedRoute": routed_route,
                    "sourceKind": interpretation["sourceKind"],
                    "chosenHorizon": interpretation["recommendedHorizon"],
                    "sourceText": source_request.get("extractedText") or source_request.get("rawText") or "",
                    "titleCandidate": interpretation.get("suggestedTitle") or source_request.get("titleCandidate"),
                    "detectedChunks": interpretation.get("detectedChunks", []),
                    "assumptions": interpretation.get("assumptions", []),
                },
                "app_context": envelope.app_context.model_dump(mode="json"),
                "presentation_context": envelope.presentation_context.model_dump(mode="json"),
                "user_authored_context": envelope.user_authored_context.model_dump(mode="json"),
                "request_id": envelope.request_id,
            },
        )
        existing_trace = bounded_plan_result.trace.agent_trace or {}
        bounded_plan_result.trace.agent_trace = {
            **existing_trace,
            "orchestration_profile": "generate_from_source",
            "substeps": [
                {
                    "operation_name": "source_interpret",
                    "artifact": source_result.artifact,
                },
                {
                    "operation_name": "bounded_plan_generate",
                    "artifact": bounded_plan_result.artifact,
                },
            ],
        }
        return bounded_plan_result

    def run_structured_output(self, *, skill, payload, context: RuntimeContext):
        preview = skill.build_prompt_preview(payload, context)
        self.tool_registry.resolve_many(skill.policy.allowed_tools)
        model_runtime = build_model_runtime(
            task_name=context.operation_name,
            task_kind=skill.policy.task_kind,
            temperature=skill.policy.temperature,
            max_tokens=skill.policy.max_tokens,
        )
        structured_output_method = self._structured_output_method_for_provider(model_runtime.provider)
        provider_request = self._provider_request_payload(
            context=context,
            skill=skill,
            model_runtime=model_runtime,
            payload=payload,
            prompt_preview=preview,
            response_mode="structured",
            structured_output_method=structured_output_method,
        )

        try:
            structured_kwargs = (
                {"method": structured_output_method}
                if structured_output_method
                else {}
            )
            structured = model_runtime.client.with_structured_output(
                skill.output_model,
                **structured_kwargs,
            )
            raw_artifact = self._invoke_provider_with_retry(
                model_runtime.provider,
                lambda: structured.invoke(
                    [
                        SystemMessage(content=preview.system_prompt),
                        HumanMessage(content=preview.user_prompt),
                    ]
                ),
            )
        except Exception as error:  # pragma: no cover - provider exceptions vary
            if self._is_retryable_provider_error(model_runtime.provider, error):
                write_provider_exchange_log(
                    request=provider_request,
                    response={
                        "status": "structured_error_fallback",
                        "error_type": error.__class__.__name__,
                        "error": str(error),
                        "fallback_strategy": "text_json",
                    },
                )
                return self._run_text_json_fallback(
                    skill=skill,
                    payload=payload,
                    context=context,
                    structured_error=error,
                )
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
                "validated_artifact": artifact.model_dump(mode="json", exclude_none=True),
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
            response = self._invoke_provider_with_retry(
                model_runtime.provider,
                lambda: model_runtime.client.invoke(
                    [
                        SystemMessage(content=preview.system_prompt),
                        HumanMessage(content=preview.user_prompt),
                    ]
                ),
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
