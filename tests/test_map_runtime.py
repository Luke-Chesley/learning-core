from __future__ import annotations

from unittest.mock import patch

from learning_core.runtime.engine import AgentEngine
from learning_core.skills.activity_generate.packs.geography import engine as geo_engine
from learning_core.skills.catalog import build_skill_registry


_SOURCE_ID = "geoboundaries:USA:ADM1"
_MOCK_BUNDLE = {
    "sourceId": _SOURCE_ID,
    "metadata": {"boundaryName": "United States of America"},
    "featureCollection": {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "id": "california",
                "properties": {"shapeName": "California"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[-124.5, 32.5], [-124.5, 42.0], [-114.0, 42.0], [-114.0, 32.5], [-124.5, 32.5]]],
                },
            },
            {
                "type": "Feature",
                "id": "oregon",
                "properties": {"shapeName": "Oregon"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[-124.7, 42.0], [-124.7, 46.2], [-116.4, 46.2], [-116.4, 42.0], [-124.7, 42.0]]],
                },
            },
        ],
    },
    "cachePath": "/tmp/mock-geography-cache",
}

_MAP_WIDGET = {
    "surfaceKind": "map_surface",
    "engineKind": "map_geojson",
    "version": "1",
    "instructionText": "Select California on the map.",
    "surface": {
        "projection": "equal_earth",
        "basemapStyle": "none",
        "center": {"lon": -120.0, "lat": 39.0},
        "zoom": 4.0,
    },
    "display": {
        "surfaceRole": "primary",
        "showLegend": True,
        "showLabels": True,
        "showInstructionsPanel": True,
        "allowLayerToggle": True,
    },
    "state": {
        "sourceId": _SOURCE_ID,
        "activeLayerIds": ["geoboundaries-usa-adm1-base"],
        "selectedFeatureIds": [],
        "markerCoordinate": None,
        "drawnPath": [],
        "labelAssignments": {},
        "timelineYear": None,
    },
    "interaction": {
        "mode": "select_region",
        "submissionMode": "explicit_submit",
        "allowReset": True,
        "resetPolicy": "reset_to_initial",
        "attemptPolicy": "allow_retry",
        "selectionBehavior": "single",
    },
    "feedback": {"mode": "explicit_submit", "displayMode": "inline"},
    "layers": [
        {
            "id": "geoboundaries-usa-adm1-base",
            "sourceId": _SOURCE_ID,
            "featureIds": ["california", "oregon"],
            "labelField": "shapeName",
            "visible": True,
            "stylePreset": "political",
        }
    ],
    "evaluation": {
        "acceptedFeatureIds": ["california"],
        "featureSelectionMode": "exact",
        "requiredCount": 1,
        "minimumCoverage": 1.0,
    },
    "annotations": {
        "legendTitle": "United States of America",
        "guidedPrompts": [],
        "callouts": [],
        "teacherNotes": None,
    },
}


def _widget_transition_envelope(learner_action, current_response=None):
    return {
        "input": {
            "activityId": "activity-1",
            "componentId": "map-1",
            "componentType": "interactive_widget",
            "widget": _MAP_WIDGET,
            "learnerAction": learner_action,
            "currentResponse": current_response,
            "attemptMetadata": {
                "attemptId": "attempt-1",
                "source": "component_action",
            },
        },
        "app_context": {
            "product": "homeschool-v2",
            "surface": "learner_activity",
        },
    }


@patch.object(geo_engine, "fetch_source_collection", return_value=_MOCK_BUNDLE)
def test_widget_transition_select_feature_updates_map_response(_mock_fetch):
    engine = AgentEngine(build_skill_registry())
    result = engine.execute(
        "widget_transition",
        _widget_transition_envelope({"type": "select_feature", "featureId": "california"}),
    )

    assert result.artifact["accepted"] is True
    assert result.artifact["nextResponse"]["selectedFeatureIds"] == ["california"]
    assert result.artifact["canonicalWidget"]["state"]["selectedFeatureIds"] == ["california"]


def test_activity_feedback_map_widget_uses_deterministic_path():
    activity_spec = {
        "schemaVersion": "2",
        "title": "Map practice",
        "purpose": "Select California.",
        "activityKind": "guided_practice",
        "linkedObjectiveIds": [],
        "linkedSkillLabels": ["regions"],
        "estimatedMinutes": 10,
        "interactionMode": "digital",
        "components": [
            {
                "type": "interactive_widget",
                "id": "map-1",
                "prompt": "Select California on the map.",
                "required": True,
                "widget": _MAP_WIDGET,
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
    envelope = {
        "input": {
            "activityId": "activity-1",
            "activitySpec": activity_spec,
            "componentId": "map-1",
            "componentType": "interactive_widget",
            "learnerResponse": ["california"],
            "attemptMetadata": {"attemptId": "attempt-1", "source": "component_action"},
        },
        "app_context": {
            "product": "homeschool-v2",
            "surface": "learner_activity",
        },
    }

    engine = AgentEngine(build_skill_registry())
    result = engine.execute("activity_feedback", envelope)

    assert result.artifact["status"] == "correct"
    assert result.artifact["widgetEngineKind"] == "map_geojson"
    assert result.artifact["evaluationMethod"] == "deterministic"
