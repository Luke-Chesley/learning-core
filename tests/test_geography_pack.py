"""Tests for the geography pack using mocked real-source geometry bundles."""
from __future__ import annotations

import json
from unittest.mock import patch

from learning_core.agent import AgentResult
from learning_core.contracts.activity import ActivityArtifact, ActivityGenerationInput
from learning_core.contracts.operation import AppContext, PresentationContext, UserAuthoredContext
from learning_core.runtime.context import RuntimeContext
from learning_core.runtime.engine import AgentEngine
from learning_core.runtime.providers import ModelRuntime
from learning_core.skills.activity_generate.packs.geography import engine as geo_engine
from learning_core.skills.activity_generate.packs.geography.engine import (
    build_widget_config,
    describe_source,
    evaluate_feature_selection,
    evaluate_labels,
    evaluate_marker,
    validate_widget_config,
)
from learning_core.skills.activity_generate.packs.geography.pack import GeographyPack
from learning_core.skills.activity_generate.validation.widgets import normalize_and_validate_widget_activity
from learning_core.skills.catalog import build_skill_registry


_LESSON_DRAFT = {
    "schema_version": "1.0",
    "title": "US regions map study",
    "lesson_focus": "Locate western states and explain what boundaries define them.",
    "primary_objectives": ["Locate western states", "Explain state borders"],
    "success_criteria": ["Select California", "Name one bordering state"],
    "total_minutes": 30,
    "blocks": [],
    "materials": [],
    "teacher_notes": [],
    "adaptations": [],
}

_SOURCE_ID = "geoboundaries:USA:ADM1"

_MOCK_BUNDLE = {
    "sourceId": _SOURCE_ID,
    "metadata": {
        "boundaryName": "United States of America",
        "boundarySource": "United States Census Bureau, MAF/TIGER Database",
        "boundaryLicense": "Public Domain",
    },
    "featureCollection": {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "id": "california",
                "properties": {"shapeName": "California", "shapeID": "USA-ADM1-CA"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[-124.5, 32.5], [-124.5, 42.0], [-114.0, 42.0], [-114.0, 32.5], [-124.5, 32.5]]],
                },
            },
            {
                "type": "Feature",
                "id": "oregon",
                "properties": {"shapeName": "Oregon", "shapeID": "USA-ADM1-OR"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[-124.7, 42.0], [-124.7, 46.2], [-116.4, 46.2], [-116.4, 42.0], [-124.7, 42.0]]],
                },
            },
            {
                "type": "Feature",
                "id": "washington",
                "properties": {"shapeName": "Washington", "shapeID": "USA-ADM1-WA"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[-124.8, 45.5], [-124.8, 49.1], [-116.8, 49.1], [-116.8, 45.5], [-124.8, 45.5]]],
                },
            },
        ],
    },
    "cachePath": "/tmp/mock-geography-cache",
}


def _context() -> RuntimeContext:
    return RuntimeContext.create(
        operation_name="activity_generate",
        app_context=AppContext(product="test", surface="test"),
        presentation_context=PresentationContext(),
        user_authored_context=UserAuthoredContext(),
    )


def _fake_runtime():
    class _Stub:
        def invoke(self, _messages):
            return type(
                "Response",
                (),
                {
                    "content": json.dumps(
                        {
                            "recommendedSourceId": _SOURCE_ID,
                            "recommendedInteractionMode": "select_region",
                            "teachingArtifactMode": False,
                            "suggestedFeatureIds": ["california"],
                            "rationale": "The lesson is about selecting a state boundary.",
                            "compareSourceId": None,
                        }
                    )
                },
            )()

    return ModelRuntime(
        provider="test",
        model="test",
        client=_Stub(),
        temperature=0.0,
        max_tokens=1024,
        max_tokens_source="test",
        provider_settings={},
    )


def _map_activity(widget: dict) -> ActivityArtifact:
    return ActivityArtifact.model_validate(
        {
            "schemaVersion": "2",
            "title": "California identification",
            "purpose": "Use the map to identify California.",
            "activityKind": "guided_practice",
            "linkedObjectiveIds": [],
            "linkedSkillTitles": ["regions"],
            "estimatedMinutes": 10,
            "interactionMode": "digital",
            "components": [
                {
                    "type": "interactive_widget",
                    "id": "map-1",
                    "prompt": "Select California on the map.",
                    "required": True,
                    "widget": widget,
                }
            ],
            "completionRules": {"strategy": "all_interactive_components"},
            "evidenceSchema": {
                "captureKinds": ["answer_response"],
                "requiresReview": False,
                "autoScorable": True,
            },
            "scoringModel": {
                "mode": "correctness_based",
                "masteryThreshold": 0.8,
                "reviewThreshold": 0.6,
            },
        }
    )


@patch.object(geo_engine, "fetch_source_collection", return_value=_MOCK_BUNDLE)
def test_geography_pack_exposes_tools_and_specs(_mock_fetch):
    pack = GeographyPack()
    tool_names = [tool.name for tool in pack.tools()]
    assert "map_validate_widget_config" in tool_names
    assert "map_generate_guided_artifact" in tool_names
    assert "ui_widgets/map_surface__geojson.md" in pack.auto_injected_ui_specs()


def test_geography_pack_needs_planning_for_map_centered_lesson():
    pack = GeographyPack()
    payload = ActivityGenerationInput.model_validate(
        {
            "learner_name": "Alex",
            "subject": "Geography",
            "linked_skill_titles": ["California map"],
            "lesson_draft": _LESSON_DRAFT,
        }
    )
    assert pack.needs_planning(payload, _context()) is True
    result = pack.run_planning_phase(payload, _context(), _fake_runtime())
    assert result is not None
    assert result.structured_data["phase"] == "geography_map_planning"
    assert result.structured_data["plan"]["recommendedSourceId"] == _SOURCE_ID


@patch.object(geo_engine, "fetch_source_collection", return_value=_MOCK_BUNDLE)
def test_geography_build_and_validate_widget_config(_mock_fetch):
    widget = build_widget_config(
        source_id=_SOURCE_ID,
        interaction_mode="select_region",
        feature_ids=["california", "oregon"],
        prompt_text="Select California on the map.",
    )
    report = validate_widget_config(widget)

    assert widget["engineKind"] == "map_geojson"
    assert widget["state"]["sourceId"] == _SOURCE_ID
    assert report["valid"] is True
    assert report["sourceTitle"] == "United States of America"


@patch.object(geo_engine, "fetch_source_collection", return_value=_MOCK_BUNDLE)
def test_geography_pack_validator_accepts_valid_map_widget(_mock_fetch):
    widget = build_widget_config(
        source_id=_SOURCE_ID,
        interaction_mode="select_region",
        feature_ids=["california", "oregon"],
        prompt_text="Select California on the map.",
    )
    artifact = _map_activity(widget)
    normalized, hard_errors, soft_warnings = normalize_and_validate_widget_activity(artifact, [GeographyPack()])

    assert normalized.components[0].widget.engineKind == "map_geojson"
    assert hard_errors == []
    assert soft_warnings == []


def test_geography_evaluation_helpers_cover_selection_marker_and_labels():
    selection = evaluate_feature_selection(
        accepted_feature_ids=["california"],
        learner_feature_ids=["california"],
    )
    marker = evaluate_marker(
        learner_coordinate={"lon": -119.5, "lat": 37.0},
        target_coordinate={"coordinate": {"lon": -119.7, "lat": 36.9}, "toleranceKm": 50.0},
    )
    labels = evaluate_labels(
        learner_labels={"california": "California"},
        label_targets=[{"featureId": "california", "correctLabel": "California"}],
    )

    assert selection["status"] == "correct"
    assert marker["status"] == "correct"
    assert labels["status"] == "correct"


@patch("learning_core.skills.activity_generate.scripts.main.run_agent_loop")
@patch("learning_core.skills.activity_generate.scripts.main.build_model_runtime")
def test_geography_request_gets_geography_tools(mock_build_runtime, mock_agent_loop, tmp_path):
    import os

    os.environ["LEARNING_CORE_LOG_DIR"] = str(tmp_path / "logs")
    mock_build_runtime.return_value = _fake_runtime()
    mock_agent_loop.return_value = AgentResult(
        final_text=json.dumps(
            {
                "schemaVersion": "2",
                "title": "Map practice",
                "purpose": "Use a map widget.",
                "activityKind": "guided_practice",
                "linkedObjectiveIds": [],
                "linkedSkillTitles": ["California map"],
                "estimatedMinutes": 10,
                "interactionMode": "digital",
                "components": [{"type": "paragraph", "id": "intro", "text": "Select the state."}],
                "completionRules": {"strategy": "all_interactive_components"},
                "evidenceSchema": {
                    "captureKinds": ["answer_response"],
                    "requiresReview": False,
                    "autoScorable": False,
                },
                "scoringModel": {
                    "mode": "completion_based",
                    "masteryThreshold": 0.8,
                    "reviewThreshold": 0.6,
                },
            }
        ),
        tool_calls=[],
        messages=[],
    )

    envelope = {
        "input": {
            "learner_name": "Test",
            "subject": "Geography",
            "linked_skill_titles": ["California map"],
            "lesson_draft": _LESSON_DRAFT,
        },
        "app_context": {"product": "test", "surface": "test"},
    }
    engine = AgentEngine(build_skill_registry())
    result = engine.execute("activity_generate", envelope)

    active = result.trace.agent_trace["active_tools"]
    assert "map_validate_widget_config" in active
    assert "map_build_widget_config" in active
    assert result.trace.agent_trace["included_packs"] == ["geography"]
    os.environ.pop("LEARNING_CORE_LOG_DIR", None)


@patch.object(geo_engine, "fetch_source_collection", return_value=_MOCK_BUNDLE)
def test_describe_source_returns_feature_summary(_mock_fetch):
    description = describe_source(_SOURCE_ID)
    assert description["featureCount"] == 3
    assert description["featureSample"][0] == "California"
