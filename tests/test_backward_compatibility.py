"""Verify non-activity skills still use the deterministic StructuredOutputSkill path."""
from learning_core.skills.base import StructuredOutputSkill
from learning_core.skills.catalog import build_skill_registry
from learning_core.skills.activity_generate.scripts.main import ActivityGenerateSkill


def test_activity_generate_is_not_structured_output_skill():
    """ActivityGenerateSkill overrides execute and is no longer a StructuredOutputSkill."""
    skill = ActivityGenerateSkill()
    assert not isinstance(skill, StructuredOutputSkill)


def test_other_skills_are_structured_output_skills():
    """All non-activity skills should still inherit from StructuredOutputSkill."""
    registry = build_skill_registry()
    deterministic_operations = {
        "activity_feedback",
        "widget_transition",
        "session_generate",
        "source_interpret",
        "curriculum_intake",
        "curriculum_generate",
        "curriculum_revise",
        "progression_generate",
        "progression_revise",
        "session_evaluate",
        "curriculum_update_propose",
    }
    for name in deterministic_operations:
        skill = registry.get(name)
        assert isinstance(skill, StructuredOutputSkill), (
            f"Expected {name} to be a StructuredOutputSkill but got {type(skill).__name__}"
        )


def test_activity_generate_response_has_standard_shape():
    """The activity_generate operation descriptor is still present in the registry."""
    registry = build_skill_registry()
    descriptors = {op.operation_name: op for op in registry.list_operations()}
    assert "activity_generate" in descriptors
    desc = descriptors["activity_generate"]
    assert desc.skill_name == "activity_generate"
    assert "read_ui_spec" in desc.allowed_tools


def test_execution_trace_accepts_agent_trace_field():
    """ExecutionTrace can carry an optional agent_trace dict without breaking existing callers."""
    from learning_core.observability.traces import ExecutionTrace, PromptPreview
    from learning_core.contracts.operation import (
        AppContext,
        OperationEnvelope,
        PresentationContext,
        UserAuthoredContext,
    )

    # Without agent_trace (backward compatible)
    trace_no_agent = ExecutionTrace(
        request_id="abc",
        operation_name="session_generate",
        allowed_tools=[],
        prompt_preview=PromptPreview(system_prompt="sys", user_prompt="usr"),
        request_envelope=OperationEnvelope(
            input={},
            app_context=AppContext(product="test", surface="test"),
            presentation_context=PresentationContext(),
            user_authored_context=UserAuthoredContext(),
        ),
    )
    assert trace_no_agent.agent_trace is None
    dumped = trace_no_agent.model_dump(mode="json", exclude_none=True)
    assert "agent_trace" not in dumped

    # With agent_trace
    trace_with_agent = ExecutionTrace(
        request_id="def",
        operation_name="activity_generate",
        allowed_tools=["read_ui_spec"],
        prompt_preview=PromptPreview(system_prompt="sys", user_prompt="usr"),
        request_envelope=OperationEnvelope(
            input={},
            app_context=AppContext(product="test", surface="test"),
            presentation_context=PresentationContext(),
            user_authored_context=UserAuthoredContext(),
        ),
        agent_trace={
            "tool_calls": [{"tool": "read_ui_spec", "args": {"path": "x.md"}, "output_length": 100}],
            "ui_specs_read": ["x.md"],
            "repair_attempted": False,
            "repair_succeeded": False,
        },
    )
    assert trace_with_agent.agent_trace is not None
    dumped = trace_with_agent.model_dump(mode="json")
    assert "agent_trace" in dumped
    assert dumped["agent_trace"]["repair_attempted"] is False
