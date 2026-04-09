from pathlib import Path

import learning_core.runtime.engine as engine_module
from learning_core.contracts.activity import ActivityArtifact, ActivityGenerationInput
from learning_core.contracts.operation import AppContext, PresentationContext, UserAuthoredContext
from learning_core.runtime.context import RuntimeContext
from learning_core.runtime.engine import AgentEngine
from learning_core.runtime.providers import ModelRuntime
from learning_core.skills.catalog import build_skill_registry
from learning_core.skills.activity_generate.scripts.main import ActivityGenerateSkill


def test_activity_generate_preview_includes_lesson_title():
    payload = ActivityGenerationInput.model_validate(
        {
            "learner_name": "Alex",
            "workflow_mode": "family_guided",
            "subject": "Math",
            "linked_skill_titles": ["Long Division"],
            "lesson_draft": {
                "schema_version": "1.0",
                "title": "Long Division",
                "lesson_focus": "Learn the long division algorithm.",
                "primary_objectives": ["Divide with support"],
                "success_criteria": ["Finish three problems"],
                "total_minutes": 35,
                "blocks": [
                    {
                        "type": "model",
                        "title": "Model it",
                        "minutes": 10,
                        "purpose": "Show the method",
                        "teacher_action": "Demonstrate on whiteboard",
                        "learner_action": "Take notes",
                        "materials_needed": [],
                        "optional": False,
                    }
                ],
                "materials": ["Workbook"],
                "teacher_notes": ["Use D-M-S-B language"],
                "adaptations": [],
                "assessment_artifact": "Workbook page",
            },
        }
    )

    preview = ActivityGenerateSkill().build_prompt_preview(
        payload,
        RuntimeContext.create(
            operation_name="activity_generate",
            app_context=AppContext(product="homeschool-v2", surface="today_workspace"),
            presentation_context=PresentationContext(),
            user_authored_context=UserAuthoredContext(),
        ),
    )

    assert "Long Division" in preview.user_prompt
    assert "ActivitySpec" in preview.system_prompt


def test_activity_artifact_accepts_canonical_minimal_spec():
    artifact = ActivityArtifact.model_validate(
        {
            "schemaVersion": "2",
            "title": "Place Value Practice",
            "purpose": "Practice identifying digit place values in 5-digit numbers.",
            "activityKind": "guided_practice",
            "linkedObjectiveIds": [],
            "linkedSkillTitles": ["place value"],
            "estimatedMinutes": 15,
            "interactionMode": "digital",
            "components": [
                {
                    "type": "paragraph",
                    "id": "intro",
                    "text": "Work through the following steps.",
                },
                {
                    "type": "short_answer",
                    "id": "q1",
                    "prompt": "What is the value of the digit 4 in 34,827?",
                    "hint": "Think about which place the 4 occupies.",
                    "required": True,
                },
                {
                    "type": "confidence_check",
                    "id": "confidence",
                    "prompt": "How confident are you?",
                    "labels": ["Not yet", "A little", "Getting there", "Pretty good", "Got it!"],
                },
            ],
            "completionRules": {"strategy": "all_interactive_components"},
            "evidenceSchema": {
                "captureKinds": ["answer_response", "confidence_signal"],
                "requiresReview": False,
                "autoScorable": False,
            },
            "scoringModel": {
                "mode": "completion_based",
                "masteryThreshold": 0.8,
                "reviewThreshold": 0.6,
            },
        }
    )

    assert artifact.schemaVersion == "2"
    assert artifact.components[1].type == "short_answer"


def test_activity_artifact_json_schema_has_no_open_objects():
    schema = ActivityArtifact.model_json_schema()
    open_paths: list[str] = []
    tuple_paths: list[str] = []
    format_paths: list[str] = []

    def walk(node, path: str) -> None:
        if isinstance(node, dict):
            is_object = node.get("type") == "object" or "properties" in node
            if is_object and node.get("additionalProperties") is not False:
                open_paths.append(path)
            if "prefixItems" in node:
                tuple_paths.append(path)
            if "format" in node:
                format_paths.append(path)
            for key, value in node.items():
                walk(value, f"{path}.{key}")
        elif isinstance(node, list):
            for index, value in enumerate(node):
                walk(value, f"{path}[{index}]")

    walk(schema, "$")

    assert open_paths == []
    assert tuple_paths == []
    assert format_paths == []


class _FakeStructuredInvoker:
    def __init__(self, artifact: dict) -> None:
        self.artifact = artifact

    def invoke(self, _messages):
        return self.artifact


class _FakeClient:
    def __init__(self, artifact: dict) -> None:
        self.artifact = artifact

    def with_structured_output(self, _output_model, **_kwargs):
        return _FakeStructuredInvoker(self.artifact)


def test_activity_execute_omits_null_optional_fields(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("LEARNING_CORE_LOG_DIR", str(tmp_path / "logs"))
    monkeypatch.setattr(
        engine_module,
        "build_model_runtime",
        lambda **_kwargs: ModelRuntime(
            provider="openai",
            model="fake-activity-generate",
            client=_FakeClient(
                {
                    "schemaVersion": "2",
                    "title": "Place Value Practice",
                    "purpose": "Practice identifying digit place values in 5-digit numbers.",
                    "activityKind": "guided_practice",
                    "linkedObjectiveIds": [],
                    "linkedSkillTitles": ["place value"],
                    "estimatedMinutes": 15,
                    "interactionMode": "digital",
                    "components": [
                        {
                            "type": "paragraph",
                            "id": "intro",
                            "text": "Work through the following steps.",
                            "markdown": None,
                        },
                        {
                            "type": "short_answer",
                            "id": "q1",
                            "prompt": "What is the value of the digit 4 in 34,827?",
                            "hint": "Think about which place the 4 occupies.",
                            "required": True,
                        },
                        {
                            "type": "build_steps",
                            "id": "steps",
                            "steps": [
                                {
                                    "id": "step-1",
                                    "instruction": "Read the number.",
                                    "expectedValue": None,
                                }
                            ],
                        },
                    ],
                    "completionRules": {
                        "strategy": "all_interactive_components",
                        "minimumComponents": None,
                    },
                    "evidenceSchema": {
                        "captureKinds": ["answer_response"],
                        "requiresReview": False,
                        "autoScorable": False,
                    },
                    "scoringModel": {
                        "mode": "completion_based",
                        "masteryThreshold": 0.8,
                        "reviewThreshold": 0.6,
                        "rubricMasteryLevel": None,
                        "confidenceMasteryLevel": None,
                    },
                }
            ),
            temperature=0.2,
            max_tokens=4096,
            max_tokens_source="test",
            provider_settings={},
        ),
    )

    engine = AgentEngine(build_skill_registry())
    result = engine.execute(
        "activity_generate",
        {
            "input": {
                "learner_name": "Alex",
                "workflow_mode": "family_guided",
                "subject": "Math",
                "linked_skill_titles": ["Long Division"],
                "lesson_draft": {
                    "schema_version": "1.0",
                    "title": "Long Division",
                    "lesson_focus": "Learn the long division algorithm.",
                    "primary_objectives": ["Divide with support"],
                    "success_criteria": ["Finish three problems"],
                    "total_minutes": 35,
                    "blocks": [
                        {
                            "type": "model",
                            "title": "Model it",
                            "minutes": 10,
                            "purpose": "Show the method",
                            "teacher_action": "Demonstrate on whiteboard",
                            "learner_action": "Take notes",
                            "materials_needed": [],
                            "optional": False,
                        }
                    ],
                    "materials": ["Workbook"],
                    "teacher_notes": ["Use D-M-S-B language"],
                    "adaptations": [],
                    "assessment_artifact": "Workbook page",
                },
            },
            "app_context": {
                "product": "homeschool-v2",
                "surface": "today_workspace",
            },
        },
    )

    paragraph = result.artifact["components"][0]
    build_steps = result.artifact["components"][2]

    assert "markdown" not in paragraph
    assert "expectedValue" not in build_steps["steps"][0]
    assert "minimumComponents" not in result.artifact["completionRules"]
    assert "rubricMasteryLevel" not in result.artifact["scoringModel"]
    assert "confidenceMasteryLevel" not in result.artifact["scoringModel"]
