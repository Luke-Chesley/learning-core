from __future__ import annotations

import json
from pathlib import Path


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "launch_eval" / "scenarios.json"
SUPPORTED_COPILOT_ACTION_KINDS = {
    "planning.adjust_day_load",
    "planning.defer_or_move_item",
    "planning.generate_today_lesson",
    "tracking.record_note",
}
SUPPORTED_SOURCE_KINDS = {
    "bounded_material",
    "timeboxed_plan",
    "structured_sequence",
    "comprehensive_source",
    "curriculum_request",
    "topic_seed",
    "shell_request",
    "ambiguous",
}


def load_fixture() -> dict:
    return json.loads(FIXTURE_PATH.read_text())


def test_launch_eval_fixture_file_exists():
    assert FIXTURE_PATH.exists()


def test_launch_eval_fixture_covers_required_source_classes():
    fixture = load_fixture()
    scenarios = fixture["scenarios"]
    required_classes = set(fixture["sourceClassesRequired"])
    observed_classes = {scenario["sourceClass"] for scenario in scenarios}

    assert observed_classes == required_classes
    assert len(scenarios) == len(required_classes)


def test_launch_eval_scenarios_include_required_rubric_sections():
    fixture = load_fixture()

    for scenario in fixture["scenarios"]:
        assert scenario["sourceInterpret"]["expectedSourceKind"] in SUPPORTED_SOURCE_KINDS
        assert scenario["sourceInterpret"]["acceptableEntryStrategies"]
        assert scenario["sourceInterpret"]["acceptableContinuationModes"]
        assert scenario["sourceInterpret"]["acceptableHorizons"]
        assert isinstance(scenario["sourceInterpret"]["requiresConfirmation"], bool)
        assert scenario["curriculumGenerate"]["expectedScale"]
        assert scenario["curriculumGenerate"]["launchPlanExpectation"]
        assert scenario["launchHandoff"]["openingLessonCountExpectation"]
        assert isinstance(scenario["launchHandoff"]["mustBeDayOneReady"], bool)
        assert scenario["sessionGenerate"]["maxScope"]
        assert isinstance(scenario["sessionGenerate"]["mustStayGroundedToCurrentSlice"], bool)
        assert isinstance(scenario["sessionGenerate"]["mustBeAgeAppropriate"], bool)
        assert scenario["copilot"]["defaultActionExpectation"]
        assert scenario["copilot"]["falsePositiveRisk"]


def test_launch_eval_copilot_action_rubric_stays_within_supported_registry():
    fixture = load_fixture()

    assert set(fixture["supportedCopilotActionKinds"]) == SUPPORTED_COPILOT_ACTION_KINDS

    for scenario in fixture["scenarios"]:
        allowed = set(scenario["copilot"]["allowedActionKinds"])
        disallowed = set(scenario["copilot"]["disallowedActionKinds"])

        assert allowed <= SUPPORTED_COPILOT_ACTION_KINDS
        assert disallowed <= SUPPORTED_COPILOT_ACTION_KINDS
        assert allowed.isdisjoint(disallowed)


def test_launch_eval_high_risk_scenarios_keep_expected_safety_constraints():
    scenario_by_class = {
        scenario["sourceClass"]: scenario
        for scenario in load_fixture()["scenarios"]
    }

    ambiguous = scenario_by_class["ambiguous_noisy_source"]
    assert ambiguous["sourceInterpret"]["expectedSourceKind"] == "ambiguous"
    assert ambiguous["sourceInterpret"]["requiresConfirmation"] is True
    assert ambiguous["launchHandoff"]["mustBeDayOneReady"] is False

    explicit_range = scenario_by_class["explicit_range_inside_large_source"]
    assert explicit_range["sourceInterpret"]["expectedSourceKind"] == "comprehensive_source"
    assert explicit_range["sourceInterpret"]["acceptableEntryStrategies"] == ["explicit_range"]

    topic_seed = scenario_by_class["topic_seed"]
    assert topic_seed["sourceInterpret"]["expectedSourceKind"] == "topic_seed"

    shell_request = scenario_by_class["shell_like_request"]
    assert shell_request["sourceInterpret"]["expectedSourceKind"] == "shell_request"
