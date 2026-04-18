"""Tests for math pack validation following chess pack test patterns."""
import json

from learning_core.contracts.activity import ActivityArtifact
from learning_core.skills.activity_generate.packs.math.pack import MathPack
from learning_core.skills.activity_generate.packs.math.tools import math_validate_widget_config
from learning_core.skills.activity_generate.packs.math.validation import MathValidator
from learning_core.skills.activity_generate.validation.widgets import normalize_and_validate_widget_activity


def _activity_with_components(components):
    return ActivityArtifact.model_validate(
        {
            "schemaVersion": "2",
            "title": "Math practice",
            "purpose": "Practice algebra skills.",
            "activityKind": "guided_practice",
            "linkedObjectiveIds": [],
            "linkedSkillLabels": ["algebra"],
            "estimatedMinutes": 8,
            "interactionMode": "digital",
            "components": components,
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


_VALID_MATH_WIDGET = {
    "surfaceKind": "expression_surface",
    "engineKind": "math_symbolic",
    "version": "1",
    "instructionText": "Solve for x.",
    "surface": {"placeholder": "x = ?", "mathKeyboard": True},
    "display": {"surfaceRole": "primary", "showPromptLatex": True},
    "state": {"promptLatex": "2x + 3 = 11", "initialValue": ""},
    "interaction": {"mode": "expression_entry", "submissionMode": "explicit_submit"},
    "feedback": {"mode": "explicit_submit", "displayMode": "inline"},
    "evaluation": {"expectedExpression": "x=4", "equivalenceMode": "equivalent"},
    "annotations": {"helperText": "Enter the full solved expression."},
}

_VALID_GRAPH_WIDGET = {
    "surfaceKind": "graph_surface",
    "engineKind": "graphing",
    "version": "1",
    "instructionText": "Plot the line.",
    "surface": {"xLabel": "x", "yLabel": "y", "grid": True},
    "display": {"surfaceRole": "primary", "showAxisLabels": True},
    "state": {"prompt": "Plot y = 2x + 1", "initialExpression": ""},
    "interaction": {"mode": "plot_curve", "submissionMode": "explicit_submit"},
    "feedback": {"mode": "explicit_submit", "displayMode": "inline"},
    "evaluation": {"expectedGraphDescription": "line with slope 2 and intercept 1"},
    "annotations": {"overlayText": "Graph the relationship."},
}


# -- Pack protocol tests --


def test_math_validators_live_under_math_pack():
    math_pack = MathPack()
    validators = math_pack.validators()
    assert len(validators) == 1
    assert isinstance(validators[0], MathValidator)


def test_math_pack_auto_injects_correct_ui_specs():
    math_pack = MathPack()
    specs = math_pack.auto_injected_ui_specs()
    assert "ui_components/interactive_widget.md" in specs
    assert "ui_widgets/expression_surface__math_symbolic.md" in specs
    assert "ui_widgets/graph_surface__graphing.md" in specs


def test_math_pack_detect_pack_widgets():
    math_pack = MathPack()
    artifact = _activity_with_components(
        [
            {
                "type": "interactive_widget",
                "id": "expr-1",
                "prompt": "Solve for x.",
                "required": True,
                "widget": {**_VALID_MATH_WIDGET},
            },
            {
                "type": "short_answer",
                "id": "explain",
                "prompt": "Explain your steps.",
                "required": True,
            },
        ]
    )
    widget_ids = math_pack.detect_pack_widgets(artifact)
    assert widget_ids == ["expr-1"]


def test_math_pack_detects_graphing_widgets():
    math_pack = MathPack()
    artifact = _activity_with_components(
        [
            {
                "type": "interactive_widget",
                "id": "graph-1",
                "prompt": "Plot the line.",
                "required": True,
                "widget": {**_VALID_GRAPH_WIDGET},
            },
        ]
    )
    widget_ids = math_pack.detect_pack_widgets(artifact)
    assert widget_ids == ["graph-1"]


def test_math_pack_required_tool_names():
    math_pack = MathPack()
    required = math_pack.required_tool_names()
    assert "math_validate_widget_config" in required


def test_math_pack_repair_guidance():
    math_pack = MathPack()
    guidance = math_pack.repair_guidance()
    assert guidance is not None
    assert "math_validate_widget_config" in guidance


# -- Math symbolic validation --


def test_valid_math_widget_no_errors():
    artifact = _activity_with_components(
        [
            {
                "type": "interactive_widget",
                "id": "expr-1",
                "prompt": "Solve for x.",
                "required": True,
                "widget": {**_VALID_MATH_WIDGET},
            }
        ]
    )
    math_pack = MathPack()
    _normalized, hard_errors, soft_warnings = normalize_and_validate_widget_activity(artifact, [math_pack])
    assert hard_errors == []
    assert soft_warnings == []


def test_expression_entry_without_expected_expression_hard_fail():
    widget = {**_VALID_MATH_WIDGET, "evaluation": {"equivalenceMode": "equivalent"}}
    artifact = _activity_with_components(
        [
            {
                "type": "interactive_widget",
                "id": "expr-1",
                "prompt": "Solve for x.",
                "required": True,
                "widget": widget,
            }
        ]
    )
    math_pack = MathPack()
    _normalized, hard_errors, _soft_warnings = normalize_and_validate_widget_activity(artifact, [math_pack])
    assert any("expectedExpression" in e for e in hard_errors)


def test_view_only_with_expected_expression_hard_fail():
    widget = {
        **_VALID_MATH_WIDGET,
        "interaction": {"mode": "view_only"},
        "feedback": {"mode": "none", "displayMode": "inline"},
    }
    artifact = _activity_with_components(
        [
            {
                "type": "interactive_widget",
                "id": "expr-1",
                "prompt": "Review this expression.",
                "required": True,
                "widget": widget,
            },
            {
                "type": "short_answer",
                "id": "q1",
                "prompt": "What did you notice?",
                "required": True,
            },
        ]
    )
    math_pack = MathPack()
    _normalized, hard_errors, _soft_warnings = normalize_and_validate_widget_activity(artifact, [math_pack])
    assert any("view_only" in e and "expectedExpression" in e for e in hard_errors)


def test_expression_entry_without_prompt_latex_hard_fail():
    widget = {
        **_VALID_MATH_WIDGET,
        "state": {"initialValue": ""},
    }
    artifact = _activity_with_components(
        [
            {
                "type": "interactive_widget",
                "id": "expr-1",
                "prompt": "Solve the problem.",
                "required": True,
                "widget": widget,
            }
        ]
    )
    math_pack = MathPack()
    _normalized, hard_errors, _soft_warnings = normalize_and_validate_widget_activity(artifact, [math_pack])
    assert any("promptLatex" in e for e in hard_errors)


def test_expression_not_primary_soft_warning():
    widget = {
        **_VALID_MATH_WIDGET,
        "display": {"surfaceRole": "supporting", "showPromptLatex": True},
    }
    artifact = _activity_with_components(
        [
            {
                "type": "interactive_widget",
                "id": "expr-1",
                "prompt": "Solve for x.",
                "required": True,
                "widget": widget,
            }
        ]
    )
    math_pack = MathPack()
    _normalized, hard_errors, soft_warnings = normalize_and_validate_widget_activity(artifact, [math_pack])
    assert not any("surfaceRole" in e for e in hard_errors)
    assert any("surfaceRole" in w and "primary" in w for w in soft_warnings)


# -- Graphing validation --


def test_valid_graphing_widget_no_errors():
    artifact = _activity_with_components(
        [
            {
                "type": "interactive_widget",
                "id": "graph-1",
                "prompt": "Plot the line.",
                "required": True,
                "widget": {**_VALID_GRAPH_WIDGET},
            }
        ]
    )
    math_pack = MathPack()
    _normalized, hard_errors, soft_warnings = normalize_and_validate_widget_activity(artifact, [math_pack])
    assert hard_errors == []
    assert soft_warnings == []


def test_graph_input_without_expected_description_hard_fail():
    widget = {**_VALID_GRAPH_WIDGET, "evaluation": {}}
    artifact = _activity_with_components(
        [
            {
                "type": "interactive_widget",
                "id": "graph-1",
                "prompt": "Plot the line.",
                "required": True,
                "widget": widget,
            }
        ]
    )
    math_pack = MathPack()
    _normalized, hard_errors, _soft_warnings = normalize_and_validate_widget_activity(artifact, [math_pack])
    assert any("expectedGraphDescription" in e for e in hard_errors)


def test_graph_view_only_with_expected_description_hard_fail():
    widget = {
        **_VALID_GRAPH_WIDGET,
        "interaction": {"mode": "view_only"},
        "feedback": {"mode": "none", "displayMode": "inline"},
    }
    artifact = _activity_with_components(
        [
            {
                "type": "interactive_widget",
                "id": "graph-1",
                "prompt": "Observe the graph.",
                "required": True,
                "widget": widget,
            },
            {
                "type": "short_answer",
                "id": "q1",
                "prompt": "What did you observe?",
                "required": True,
            },
        ]
    )
    math_pack = MathPack()
    _normalized, hard_errors, _soft_warnings = normalize_and_validate_widget_activity(artifact, [math_pack])
    assert any("view_only" in e and "expectedGraphDescription" in e for e in hard_errors)


# -- Pack isolation --


def test_no_math_pack_no_math_validators():
    """Without the math pack active, no math-specific validation runs."""
    artifact = _activity_with_components(
        [
            {
                "type": "interactive_widget",
                "id": "expr-1",
                "prompt": "Solve for x.",
                "required": True,
                "widget": {**_VALID_MATH_WIDGET},
            }
        ]
    )
    _normalized, hard_errors, _soft_warnings = normalize_and_validate_widget_activity(artifact, active_packs=[])
    assert not any("expectedExpression" in e for e in hard_errors)


# -- Tool tests --


def test_math_validate_tool_valid_symbolic():
    result = json.loads(math_validate_widget_config.invoke({
        "engine_kind": "math_symbolic",
        "interaction_mode": "expression_entry",
        "expected_expression": "x=4",
        "prompt_latex": "2x + 3 = 11",
    }))
    assert result["valid"] is True
    assert result["errors"] == []


def test_math_validate_tool_missing_expected():
    result = json.loads(math_validate_widget_config.invoke({
        "engine_kind": "math_symbolic",
        "interaction_mode": "expression_entry",
        "prompt_latex": "2x + 3 = 11",
    }))
    assert result["valid"] is False
    assert any("expectedExpression" in e for e in result["errors"])


def test_math_validate_tool_valid_graphing():
    result = json.loads(math_validate_widget_config.invoke({
        "engine_kind": "graphing",
        "interaction_mode": "plot_curve",
        "expected_graph_description": "line with slope 2",
    }))
    assert result["valid"] is True
    assert result["errors"] == []


def test_math_validate_tool_graphing_missing_description():
    result = json.loads(math_validate_widget_config.invoke({
        "engine_kind": "graphing",
        "interaction_mode": "plot_point",
    }))
    assert result["valid"] is False
    assert any("expectedGraphDescription" in e for e in result["errors"])
