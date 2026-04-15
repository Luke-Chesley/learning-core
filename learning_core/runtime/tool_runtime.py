from __future__ import annotations

from dataclasses import dataclass, field

from learning_core.runtime.policy import ExecutionPolicy
from learning_core.runtime.request_normalization import RuntimeRequest


@dataclass(frozen=True)
class ToolFamilyDefinition:
    name: str
    description: str
    tool_names: tuple[str, ...] = ()


@dataclass(frozen=True)
class ToolRuntimePlan:
    tool_families: tuple[str, ...] = ()
    allowed_tool_names: tuple[str, ...] = ()
    metadata: dict[str, object] = field(default_factory=dict)


TOOL_FAMILY_REGISTRY: dict[str, ToolFamilyDefinition] = {
    "read_context": ToolFamilyDefinition("read_context", "Read bounded runtime or workflow context."),
    "read_pack_docs": ToolFamilyDefinition("read_pack_docs", "Read bounded pack or UI/widget documentation.", ("read_ui_spec",)),
    "draft_artifact": ToolFamilyDefinition("draft_artifact", "Draft a typed artifact."),
    "propose_adjustment": ToolFamilyDefinition("propose_adjustment", "Produce bounded adjustment proposals."),
    "synthesize_evidence": ToolFamilyDefinition("synthesize_evidence", "Summarize evidence into a typed evaluation."),
    "create_recommendation": ToolFamilyDefinition("create_recommendation", "Produce recommendations or next-step summaries."),
}


def resolve_tool_runtime_plan(runtime_request: RuntimeRequest, policy: ExecutionPolicy) -> ToolRuntimePlan:
    families = tuple(sorted(set(policy.tool_families or runtime_request.task_profile_definition.tool_families)))
    allowed_tool_names = policy.allowed_tools
    if not allowed_tool_names:
        discovered: list[str] = []
        for family_name in families:
            family = TOOL_FAMILY_REGISTRY.get(family_name)
            if family is None:
                continue
            for tool_name in family.tool_names:
                if tool_name not in discovered:
                    discovered.append(tool_name)
        allowed_tool_names = tuple(discovered)
    return ToolRuntimePlan(
        tool_families=families,
        allowed_tool_names=allowed_tool_names,
        metadata={"resolved_from_task_profile": not bool(policy.allowed_tools)},
    )
