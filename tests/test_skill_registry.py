from learning_core.skills.catalog import build_skill_registry


def test_registry_contains_activity_operation():
    registry = build_skill_registry()
    assert "generate-activities-from-plan-session" in registry.list_operations()


def test_registry_contains_eight_operations():
    registry = build_skill_registry()
    assert len(registry.list_operations()) == 8
