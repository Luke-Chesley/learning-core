from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel

from learning_core.contracts.operation import AppContext, OperationEnvelope, PresentationContext, UserAuthoredContext
from learning_core.runtime.context import RuntimeContext
from learning_core.runtime.task_profiles import OperationRuntimeDefinition, TaskProfileDefinition, get_operation_runtime_definition, get_task_profile


def _infer_template(app_context: AppContext) -> str | None:
    if app_context.template:
        return app_context.template
    product = app_context.product.lower()
    if "homeschool" in product:
        return "homeschool"
    return None


def _infer_actor_role(app_context: AppContext, presentation_context: PresentationContext) -> str | None:
    if app_context.actor_role:
        return app_context.actor_role
    return {
        "parent": "adult",
        "teacher": "educator",
        "learner": "learner",
        "internal": "coach",
    }.get(presentation_context.audience)


@dataclass(frozen=True)
class RuntimeRequest:
    operation_name: str
    request_id: str
    task_profile: str
    requested_response_type: str
    workflow_card: str
    template: str | None
    workflow_mode: str | None
    surface: str
    actor_role: str | None
    autonomy_tier: str
    latency_class: str
    pack_hints: list[str]
    context_bundle: dict[str, Any]
    raw_payload: dict[str, Any]
    payload: BaseModel
    runtime_context: RuntimeContext
    app_context: AppContext
    presentation_context: PresentationContext
    user_authored_context: UserAuthoredContext
    operation_definition: OperationRuntimeDefinition
    task_profile_definition: TaskProfileDefinition


def normalize_runtime_request(operation_name: str, envelope_data: dict[str, Any], input_model: type[BaseModel]) -> RuntimeRequest:
    operation_definition = get_operation_runtime_definition(operation_name)
    task_profile_definition = get_task_profile(operation_definition.task_profile)
    envelope = OperationEnvelope.model_validate(envelope_data)
    runtime_context = RuntimeContext.create(
        operation_name=operation_name,
        request_id=envelope.request_id,
        app_context=envelope.app_context,
        presentation_context=envelope.presentation_context,
        user_authored_context=envelope.user_authored_context,
    )
    payload = input_model.model_validate(envelope.input)
    template = _infer_template(envelope.app_context)
    actor_role = _infer_actor_role(envelope.app_context, envelope.presentation_context)
    latency_class = envelope.app_context.latency_class or task_profile_definition.latency_class
    autonomy_tier = envelope.app_context.autonomy_tier or "draft"
    pack_hints = list(envelope.app_context.pack_hints)
    context_bundle = {
        "app_context": envelope.app_context.model_dump(mode="json"),
        "presentation_context": envelope.presentation_context.model_dump(mode="json"),
        "user_authored_context": envelope.user_authored_context.model_dump(mode="json"),
    }
    return RuntimeRequest(
        operation_name=operation_name,
        request_id=runtime_context.request_id,
        task_profile=operation_definition.task_profile,
        requested_response_type=operation_definition.response_type,
        workflow_card=operation_definition.workflow_card,
        template=template,
        workflow_mode=envelope.app_context.workflow_mode,
        surface=envelope.app_context.surface,
        actor_role=actor_role,
        autonomy_tier=autonomy_tier,
        latency_class=latency_class,
        pack_hints=pack_hints,
        context_bundle=context_bundle,
        raw_payload=payload.model_dump(mode="json"),
        payload=payload,
        runtime_context=runtime_context,
        app_context=envelope.app_context,
        presentation_context=envelope.presentation_context,
        user_authored_context=envelope.user_authored_context,
        operation_definition=operation_definition,
        task_profile_definition=task_profile_definition,
    )
