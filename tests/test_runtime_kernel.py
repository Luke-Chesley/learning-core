from __future__ import annotations

from learning_core.runtime.engine import AgentEngine
from learning_core.skills.catalog import build_skill_registry


def test_kernel_preview_exposes_runtime_metadata_for_session_generate():
    engine = AgentEngine(build_skill_registry())

    preview = engine.preview(
        "session_generate",
        {
            "input": {
                "topic": "Responding correctly to 1. e4",
            },
            "app_context": {
                "product": "homeschool-v2",
                "surface": "today",
            },
        },
    )

    assert preview.task_profile == "bounded_day_generation"
    assert preview.response_type == "lesson_draft"
    assert preview.workflow_card == "bounded_day_generation"
    assert preview.runtime_mode == "skill_execute"
    assert preview.selected_packs == ["homeschool"]


def test_operation_descriptors_include_runtime_mapping_metadata():
    engine = AgentEngine(build_skill_registry())

    operations = {
        operation.operation_name: operation
        for operation in engine.skill_registry.list_operations()
    }

    assert operations["session_generate"].task_profile == "bounded_day_generation"
    assert operations["session_generate"].response_type == "lesson_draft"
    assert operations["activity_generate"].workflow_card == "activity_generation"
