from learning_core.skills.catalog import build_skill_registry


def test_registry_contains_activity_operation():
    registry = build_skill_registry()
    operation_names = [operation.operation_name for operation in registry.list_operations()]
    assert "activity_generate" in operation_names
    assert "activity_feedback" in operation_names
    assert "widget_transition" in operation_names


def test_registry_contains_required_operations():
    registry = build_skill_registry()
    operation_names = {operation.operation_name for operation in registry.list_operations()}
    assert {
        "activity_generate",
        "activity_feedback",
        "widget_transition",
        "session_generate",
        "curriculum_generate",
        "curriculum_revise",
        "launch_plan_generate",
        "progression_generate",
        "progression_revise",
        "session_evaluate",
        "curriculum_intake",
        "copilot_chat",
    }.issubset(operation_names)
