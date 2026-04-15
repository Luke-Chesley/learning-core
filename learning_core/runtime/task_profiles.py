from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class TaskProfileDefinition:
    name: str
    default_response_type: str
    runtime_mode: str
    task_kind: str
    latency_class: str = "interactive"
    tool_families: tuple[str, ...] = field(default_factory=tuple)
    max_loop_steps: int = 0
    repair_attempts: int = 0
    allow_chaining: bool = False
    approval_required: bool = False


@dataclass(frozen=True)
class OperationRuntimeDefinition:
    operation_name: str
    task_profile: str
    response_type: str
    workflow_card: str
    execution_strategy: str


TASK_PROFILE_REGISTRY: dict[str, TaskProfileDefinition] = {
    profile.name: profile
    for profile in (
        TaskProfileDefinition("activity_evaluation", "activity_feedback", "skill_execute", "generation"),
        TaskProfileDefinition("adaptive_or_bounded_activity_generation", "activity_spec", "agentic_loop", "generation", tool_families=("read_pack_docs", "read_context"), max_loop_steps=8, repair_attempts=2),
        TaskProfileDefinition("artifact_revision", "curriculum_artifact_revision", "skill_execute", "generation", allow_chaining=True),
        TaskProfileDefinition("bounded_day_generation", "lesson_draft", "single_pass", "generation", repair_attempts=1),
        TaskProfileDefinition("intake_dialogue", "intake_turn", "single_pass", "chat"),
        TaskProfileDefinition("interactive_assistance", "summary", "text", "chat"),
        TaskProfileDefinition("long_horizon_planning", "curriculum_artifact", "skill_execute", "generation", latency_class="background", allow_chaining=True),
        TaskProfileDefinition("proposal_generation", "proposal", "single_pass", "generation", approval_required=True),
        TaskProfileDefinition("session_synthesis", "evaluation", "single_pass", "generation"),
        TaskProfileDefinition("source_interpret", "source_interpretation", "single_pass", "generation"),
        TaskProfileDefinition("weekly_expansion", "bounded_plan", "single_pass", "generation"),
    )
}


OPERATION_RUNTIME_MAP: dict[str, OperationRuntimeDefinition] = {
    "activity_feedback": OperationRuntimeDefinition("activity_feedback", "activity_evaluation", "activity_feedback", "activity_evaluation", "skill_execute"),
    "activity_generate": OperationRuntimeDefinition("activity_generate", "adaptive_or_bounded_activity_generation", "activity_spec", "activity_generation", "skill_execute"),
    "bounded_plan_generate": OperationRuntimeDefinition("bounded_plan_generate", "weekly_expansion", "bounded_plan", "weekly_expansion", "structured"),
    "copilot_chat": OperationRuntimeDefinition("copilot_chat", "interactive_assistance", "summary", "interactive_assistance", "text"),
    "curriculum_generate": OperationRuntimeDefinition("curriculum_generate", "long_horizon_planning", "curriculum_artifact", "long_horizon_planning", "skill_execute"),
    "curriculum_intake": OperationRuntimeDefinition("curriculum_intake", "intake_dialogue", "intake_turn", "curriculum_intake", "structured"),
    "curriculum_revise": OperationRuntimeDefinition("curriculum_revise", "artifact_revision", "curriculum_artifact_revision", "artifact_revision", "skill_execute"),
    "curriculum_update_propose": OperationRuntimeDefinition("curriculum_update_propose", "proposal_generation", "proposal", "proposal_generation", "structured"),
    "progression_generate": OperationRuntimeDefinition("progression_generate", "long_horizon_planning", "progression_artifact", "progression_generation", "structured"),
    "progression_revise": OperationRuntimeDefinition("progression_revise", "artifact_revision", "progression_artifact", "progression_revision", "structured"),
    "session_evaluate": OperationRuntimeDefinition("session_evaluate", "session_synthesis", "evaluation", "session_synthesis", "structured"),
    "session_generate": OperationRuntimeDefinition("session_generate", "bounded_day_generation", "lesson_draft", "bounded_day_generation", "structured"),
    "source_interpret": OperationRuntimeDefinition("source_interpret", "source_interpret", "source_interpretation", "source_interpret", "structured"),
    "widget_transition": OperationRuntimeDefinition("widget_transition", "interactive_assistance", "widget_transition", "widget_transition", "skill_execute"),
}


def get_task_profile(name: str) -> TaskProfileDefinition:
    return TASK_PROFILE_REGISTRY[name]


def get_operation_runtime_definition(operation_name: str) -> OperationRuntimeDefinition:
    return OPERATION_RUNTIME_MAP[operation_name]
