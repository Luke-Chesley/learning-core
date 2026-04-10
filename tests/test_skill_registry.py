from learning_core.skills.catalog import build_skill_registry


def test_registry_contains_activity_operation():
    registry = build_skill_registry()
    operation_names = [operation.operation_name for operation in registry.list_operations()]
    assert "activity_generate" in operation_names
    assert "activity_feedback" in operation_names


def test_registry_contains_required_operations():
    registry = build_skill_registry()
    operation_names = {operation.operation_name for operation in registry.list_operations()}
    assert {
        "activity_generate",
        "activity_feedback",
        "session_generate",
        "curriculum_generate",
        "curriculum_revise",
        "progression_generate",
        "progression_revise",
        "session_evaluate",
        "curriculum_update_propose",
        "curriculum_intake",
        "copilot_chat",
    }.issubset(operation_names)
