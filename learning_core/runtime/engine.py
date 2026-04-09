from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage

from learning_core.observability.traces import ExecutionLineage, ExecutionTrace, PromptPreview
from learning_core.runtime.context import RuntimeContext
from learning_core.runtime.errors import ContractValidationError, ProviderExecutionError
from learning_core.runtime.providers import build_model_runtime
from learning_core.runtime.registry import SkillRegistry
from learning_core.runtime.tooling import ToolRegistry


class AgentEngine:
    def __init__(self, skill_registry: SkillRegistry, tool_registry: ToolRegistry | None = None) -> None:
        self.skill_registry = skill_registry
        self.tool_registry = tool_registry or ToolRegistry()

    def execute(self, operation_name: str, payload: dict, request_id: str | None = None):
        skill = self.skill_registry.get(operation_name)
        context = RuntimeContext.create(operation_name=operation_name, request_id=request_id)
        parsed_payload = skill.input_model.model_validate(payload)
        return skill.execute(self, parsed_payload, context)

    def preview(self, operation_name: str, payload: dict) -> PromptPreview:
        skill = self.skill_registry.get(operation_name)
        parsed_payload = skill.input_model.model_validate(payload)
        return skill.build_prompt_preview(parsed_payload)

    def run_structured_output(self, *, skill, payload, context: RuntimeContext):
        preview = skill.build_prompt_preview(payload)
        self.tool_registry.resolve_many(skill.policy.allowed_tools)
        model_runtime = build_model_runtime(
            task_name=context.operation_name,
            task_kind="generation",
            temperature=skill.policy.temperature,
            max_tokens=skill.policy.max_tokens,
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
            raise ProviderExecutionError(str(error)) from error

        try:
            artifact = skill.output_model.model_validate(raw_artifact)
        except Exception as error:
            raise ContractValidationError(str(error)) from error

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
        )
        return artifact, lineage, trace
