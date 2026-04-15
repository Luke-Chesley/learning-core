from __future__ import annotations

import json
import re
from fractions import Fraction
from typing import Any

from learning_core.contracts.activity import ActivityComponent
from learning_core.contracts.activity_feedback import (
    ActivityFeedbackArtifact,
    ActivityFeedbackRequest,
    FeedbackScoring,
)
from learning_core.contracts.operation import OperationEnvelope
from learning_core.contracts.widgets import InteractiveWidgetPayload
from learning_core.domain.chess_engine import evaluate_move as evaluate_chess_move
from learning_core.observability.traces import ExecutionLineage, ExecutionTrace
from learning_core.runtime.policy import ExecutionPolicy
from learning_core.runtime.skill import SkillExecutionResult
from learning_core.skills.base import StructuredOutputSkill
from learning_core.skills.activity_generate.packs.geography.engine import (
    evaluate_feature_selection,
    evaluate_labels,
    evaluate_marker,
    evaluate_path,
)

_NUMERIC_PATTERN = re.compile(r"^-?\d+(?:\.\d+)?(?:/\d+)?$")


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


def _extract_component(payload: ActivityFeedbackRequest) -> ActivityComponent | None:
    if payload.activitySpec is None:
        return None
    for component in payload.activitySpec.components:
        if component.id == payload.componentId:
            return component
    return None


def _extract_widget(
    payload: ActivityFeedbackRequest,
    component: ActivityComponent | None,
) -> InteractiveWidgetPayload | None:
    if payload.widget is not None:
        return payload.widget
    if component is not None and component.type == "interactive_widget":
        return component.widget
    return None


def _extract_expected_answer(component: ActivityComponent | None, payload: ActivityFeedbackRequest) -> Any:
    if payload.expectedAnswer is not None:
        return payload.expectedAnswer

    if component is None:
        return None

    if component.type == "single_select":
        return [choice.id for choice in component.choices if choice.correct]
    if component.type == "multi_select":
        return [choice.id for choice in component.choices if choice.correct]
    if component.type == "ordered_sequence":
        ordered_items = sorted(component.items, key=lambda item: item.correctIndex)
        return [item.id for item in ordered_items]
    if component.type == "short_answer":
        return component.expectedAnswer
    if component.type == "build_steps":
        return {
            step.id: step.expectedValue
            for step in component.steps
            if step.expectedValue is not None
        }
    if component.type == "interactive_widget":
        widget = component.widget
        if widget.engineKind == "chess":
            return list(widget.evaluation.expectedMoves)
        if widget.engineKind == "math_symbolic":
            return widget.evaluation.expectedExpression
        if widget.engineKind == "graphing":
            return widget.evaluation.expectedGraphDescription
        if widget.engineKind == "map_geojson":
            return widget.evaluation.model_dump(mode="json", exclude_none=True)
    return None


def _parse_numeric_value(value: Any) -> Fraction | None:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return Fraction(str(value))
    if not isinstance(value, str):
        return None
    normalized = value.strip().replace(",", "")
    if not _NUMERIC_PATTERN.fullmatch(normalized):
        return None
    try:
        return Fraction(normalized)
    except ValueError:
        return None


def _feedback(
    *,
    component_id: str,
    component_type: str,
    status: str,
    message: str,
    confidence: float,
    hint: str | None = None,
    next_step: str | None = None,
    allow_retry: bool = True,
    evaluation_method: str = "deterministic",
    scoring: FeedbackScoring | None = None,
    widget_engine_kind: str | None = None,
) -> ActivityFeedbackArtifact:
    return ActivityFeedbackArtifact(
        schemaVersion="1",
        componentId=component_id,
        componentType=component_type,
        widgetEngineKind=widget_engine_kind,
        status=status,
        feedbackMessage=message,
        hint=hint,
        nextStep=next_step,
        confidence=confidence,
        allowRetry=allow_retry,
        evaluationMethod=evaluation_method,
        scoring=scoring,
    )


def _evaluate_single_select(
    payload: ActivityFeedbackRequest,
    component: ActivityComponent | None,
) -> ActivityFeedbackArtifact | None:
    if payload.componentType != "single_select":
        return None
    learner_value = payload.learnerResponse
    if not isinstance(learner_value, str):
        return None

    expected_value = _extract_expected_answer(component, payload)
    if not isinstance(expected_value, list) or not expected_value:
        return None

    is_correct = learner_value in expected_value
    explanation = None
    if component is not None and component.type == "single_select":
        correct_choice = next((choice for choice in component.choices if choice.correct), None)
        explanation = correct_choice.explanation if correct_choice else None

    return _feedback(
        component_id=payload.componentId,
        component_type=payload.componentType,
        status="correct" if is_correct else "incorrect",
        message="That matches the expected choice." if is_correct else "That choice does not match the expected answer.",
        confidence=0.99,
        hint=None if is_correct else explanation,
        next_step=None if is_correct else "Re-read the prompt and compare the options more carefully.",
        allow_retry=not is_correct,
        scoring=FeedbackScoring(score=1.0 if is_correct else 0.0, matchedTargets=int(is_correct), totalTargets=1),
    )


def _evaluate_multi_select(
    payload: ActivityFeedbackRequest,
    component: ActivityComponent | None,
) -> ActivityFeedbackArtifact | None:
    if payload.componentType != "multi_select":
        return None
    learner_value = payload.learnerResponse
    if not isinstance(learner_value, list) or not all(isinstance(item, str) for item in learner_value):
        return None

    expected_value = _extract_expected_answer(component, payload)
    if not isinstance(expected_value, list) or not expected_value:
        return None

    learner_set = set(learner_value)
    expected_set = set(expected_value)
    matched_count = len(learner_set & expected_set)
    score = matched_count / len(expected_set)

    if learner_set == expected_set:
        status = "correct"
        message = "You selected the full expected set."
    elif matched_count > 0:
        status = "partial"
        message = f"You found {matched_count} of {len(expected_set)} expected choices."
    else:
        status = "incorrect"
        message = "Those selections do not match the expected answers."

    return _feedback(
        component_id=payload.componentId,
        component_type=payload.componentType,
        status=status,
        message=message,
        confidence=0.98,
        hint=None if status == "correct" else "Check for missing correct choices and any extra selections.",
        next_step=None if status == "correct" else "Review the prompt and compare each option against the rule or pattern.",
        allow_retry=status != "correct",
        scoring=FeedbackScoring(score=score, matchedTargets=matched_count, totalTargets=len(expected_set)),
    )


def _evaluate_ordered_sequence(
    payload: ActivityFeedbackRequest,
    component: ActivityComponent | None,
) -> ActivityFeedbackArtifact | None:
    if payload.componentType != "ordered_sequence":
        return None
    learner_value = payload.learnerResponse
    expected_value = _extract_expected_answer(component, payload)
    if (
        not isinstance(learner_value, list)
        or not all(isinstance(item, str) for item in learner_value)
        or not isinstance(expected_value, list)
        or not all(isinstance(item, str) for item in expected_value)
    ):
        return None

    matched_positions = sum(
        1
        for learner_item, expected_item in zip(learner_value, expected_value)
        if learner_item == expected_item
    )
    total_targets = len(expected_value)
    score = matched_positions / total_targets if total_targets else 0.0

    if learner_value == expected_value:
        status = "correct"
        message = "The sequence is in the expected order."
    elif matched_positions > 0:
        status = "partial"
        message = f"You have {matched_positions} of {total_targets} positions in the right place."
    else:
        status = "incorrect"
        message = "The order does not match the expected sequence."

    return _feedback(
        component_id=payload.componentId,
        component_type=payload.componentType,
        status=status,
        message=message,
        confidence=0.98,
        hint=None if status == "correct" else "Look for the first step that should happen before the others.",
        next_step=None if status == "correct" else "Try fixing the earliest out-of-place item first.",
        allow_retry=status != "correct",
        scoring=FeedbackScoring(score=score, matchedTargets=matched_positions, totalTargets=total_targets),
    )


def _evaluate_short_answer(
    payload: ActivityFeedbackRequest,
    component: ActivityComponent | None,
) -> ActivityFeedbackArtifact | None:
    if payload.componentType != "short_answer":
        return None
    learner_value = payload.learnerResponse
    expected_value = _extract_expected_answer(component, payload)
    if not isinstance(learner_value, str) or not isinstance(expected_value, str):
        return None

    normalized_learner = _normalize_text(learner_value)
    normalized_expected = _normalize_text(expected_value)
    numeric_learner = _parse_numeric_value(learner_value)
    numeric_expected = _parse_numeric_value(expected_value)

    is_correct = normalized_learner == normalized_expected
    if numeric_learner is not None and numeric_expected is not None:
        is_correct = numeric_learner == numeric_expected

    return _feedback(
        component_id=payload.componentId,
        component_type=payload.componentType,
        status="correct" if is_correct else "incorrect",
        message="That answer matches the expected result." if is_correct else "That answer does not match the expected result.",
        confidence=0.99 if numeric_learner is not None and numeric_expected is not None else 0.97,
        hint=None if is_correct else "Check the final value and any units or notation the prompt expects.",
        next_step=None if is_correct else "Work the problem again and compare your final answer carefully.",
        allow_retry=not is_correct,
        scoring=FeedbackScoring(score=1.0 if is_correct else 0.0, matchedTargets=int(is_correct), totalTargets=1),
    )


def _evaluate_chess_widget(
    payload: ActivityFeedbackRequest,
    component: ActivityComponent | None,
) -> ActivityFeedbackArtifact | None:
    if payload.componentType != "interactive_widget":
        return None

    widget = _extract_widget(payload, component)
    if widget is None or widget.engineKind != "chess":
        return None

    expected_value = _extract_expected_answer(component, payload)
    if not isinstance(expected_value, list) or not expected_value:
        return None

    try:
        result = evaluate_chess_move(widget.state.fen, payload.learnerResponse, expected_value)
    except ValueError as error:
        return _feedback(
            component_id=payload.componentId,
            component_type=payload.componentType,
            widget_engine_kind=widget.engineKind,
            status="incorrect",
            message="That move is not legal from this position.",
            confidence=0.99,
            hint="Check whose turn it is and whether the selected move is legal.",
            next_step="Choose a legal move from the current position.",
            allow_retry=True,
            scoring=FeedbackScoring(score=0.0, matchedTargets=0, totalTargets=1, rubricNotes=str(error)),
        )

    is_correct = result["status"] == "correct"
    return _feedback(
        component_id=payload.componentId,
        component_type=payload.componentType,
        widget_engine_kind=widget.engineKind,
        status="correct" if is_correct else "incorrect",
        message="That move matches the expected move." if is_correct else "That move does not match the expected move for this position.",
        confidence=0.99,
        hint=None if is_correct else "Look again at the immediate tactical or positional goal in the position.",
        next_step=None if is_correct else "Reset the board and try the move that best addresses the prompt.",
        allow_retry=not is_correct,
        scoring=FeedbackScoring(score=1.0 if is_correct else 0.0, matchedTargets=int(is_correct), totalTargets=1),
    )


def _normalize_math_text_response(learner_response: Any, key: str) -> str | None:
    if isinstance(learner_response, str):
        return learner_response
    if isinstance(learner_response, dict):
        value = learner_response.get(key)
        if isinstance(value, str):
            return value
    return None


def _evaluate_math_symbolic_widget(
    payload: ActivityFeedbackRequest,
    component: ActivityComponent | None,
) -> ActivityFeedbackArtifact | None:
    if payload.componentType != "interactive_widget":
        return None

    widget = _extract_widget(payload, component)
    if widget is None or widget.engineKind != "math_symbolic":
        return None

    expected_value = _extract_expected_answer(component, payload)
    learner_value = _normalize_math_text_response(payload.learnerResponse, "value")
    if not isinstance(expected_value, str) or learner_value is None:
        return None

    normalized_learner = _normalize_text(learner_value)
    normalized_expected = _normalize_text(expected_value)
    is_correct = normalized_learner == normalized_expected

    if widget.evaluation.equivalenceMode != "exact":
        compact_learner = re.sub(r"\s+", "", learner_value)
        compact_expected = re.sub(r"\s+", "", expected_value)
        is_correct = compact_learner == compact_expected

    return _feedback(
        component_id=payload.componentId,
        component_type=payload.componentType,
        widget_engine_kind=widget.engineKind,
        status="correct" if is_correct else "incorrect",
        message="That symbolic answer matches the expected expression." if is_correct else "That symbolic answer does not match the expected expression.",
        confidence=0.98,
        hint=None if is_correct else "Check the final solved expression and make sure you entered the complete symbolic answer.",
        next_step=None if is_correct else "Revise the expression and compare it carefully to the prompt.",
        allow_retry=not is_correct,
        scoring=FeedbackScoring(score=1.0 if is_correct else 0.0, matchedTargets=int(is_correct), totalTargets=1),
    )


def _evaluate_graphing_widget(
    payload: ActivityFeedbackRequest,
    component: ActivityComponent | None,
) -> ActivityFeedbackArtifact | None:
    if payload.componentType != "interactive_widget":
        return None

    widget = _extract_widget(payload, component)
    if widget is None or widget.engineKind != "graphing":
        return None

    learner_value = _normalize_math_text_response(payload.learnerResponse, "expression")
    if learner_value is None:
        return None

    expected_value = _extract_expected_answer(component, payload)
    if not isinstance(expected_value, str) or not expected_value.strip():
        return None

    normalized_learner = _normalize_text(learner_value)
    normalized_expected = _normalize_text(expected_value)
    if normalized_learner == normalized_expected:
        return _feedback(
            component_id=payload.componentId,
            component_type=payload.componentType,
            widget_engine_kind=widget.engineKind,
            status="correct",
            message="That graph entry matches the expected description.",
            confidence=0.97,
            allow_retry=False,
            scoring=FeedbackScoring(score=1.0, matchedTargets=1, totalTargets=1),
        )

    # Graphing still relies on a lighter-weight heuristic path until a true graph evaluator exists.
    return _feedback(
        component_id=payload.componentId,
        component_type=payload.componentType,
        widget_engine_kind=widget.engineKind,
        status="needs_review",
        message="Graph input captured. This response needs review against the expected graph description.",
        confidence=0.72,
        hint="Use the prompt and the expected line description to check slope, intercept, or plotted shape.",
        next_step="Adjust the graph entry or review it with the teacher.",
        allow_retry=True,
        scoring=FeedbackScoring(score=0.5, matchedTargets=0, totalTargets=1),
    )


def _evaluate_map_widget(
    payload: ActivityFeedbackRequest,
    component: ActivityComponent | None,
) -> ActivityFeedbackArtifact | None:
    if payload.componentType != "interactive_widget":
        return None

    widget = _extract_widget(payload, component)
    if widget is None or widget.engineKind != "map_geojson":
        return None

    expected_value = _extract_expected_answer(component, payload)
    if not isinstance(expected_value, dict):
        return None

    result: dict[str, Any] | None = None
    learner_response = payload.learnerResponse
    mode = widget.interaction.mode

    if isinstance(learner_response, dict):
        if mode in {"select_region", "multi_select_regions"} and isinstance(learner_response.get("selectedFeatureIds"), list):
            learner_response = learner_response["selectedFeatureIds"]
        elif mode == "place_marker" and isinstance(learner_response.get("markerCoordinate"), dict):
            learner_response = learner_response["markerCoordinate"]
        elif mode == "trace_path" and isinstance(learner_response.get("drawnPath"), list):
            learner_response = learner_response["drawnPath"]
        elif mode == "label_regions" and isinstance(learner_response.get("labelAssignments"), dict):
            learner_response = learner_response["labelAssignments"]

    if mode in {"select_region", "multi_select_regions"}:
        if not isinstance(learner_response, list) or not all(isinstance(item, str) for item in learner_response):
            return None
        result = evaluate_feature_selection(
            accepted_feature_ids=list(expected_value.get("acceptedFeatureIds") or []),
            learner_feature_ids=learner_response,
            selection_mode=str(expected_value.get("featureSelectionMode") or "exact"),
        )
    elif mode == "place_marker":
        if not isinstance(learner_response, dict):
            return None
        result = evaluate_marker(
            learner_coordinate=learner_response,
            target_coordinate=expected_value.get("markerTarget"),
        )
    elif mode == "trace_path":
        if not isinstance(learner_response, list):
            return None
        result = evaluate_path(
            learner_points=learner_response,
            expected_path=expected_value.get("expectedPath"),
        )
    elif mode == "label_regions":
        if not isinstance(learner_response, dict):
            return None
        result = evaluate_labels(
            learner_labels=learner_response,
            label_targets=list(expected_value.get("labelTargets") or []),
        )

    if result is None:
        return None

    status = result["status"]
    return _feedback(
        component_id=payload.componentId,
        component_type=payload.componentType,
        widget_engine_kind=widget.engineKind,
        status=status,
        message=(
            "That map response matches the expected answer."
            if status == "correct"
            else "That map response is partially correct."
            if status == "partial"
            else "That map response does not match the expected answer."
        ),
        confidence=0.98,
        hint=None if status == "correct" else "Check the map prompt, visible labels, and target region or route more carefully.",
        next_step=None if status == "correct" else "Revise the map response and compare it to the prompt.",
        allow_retry=status != "correct",
        scoring=FeedbackScoring(
            score=result.get("score"),
            matchedTargets=result.get("matchedTargets"),
            totalTargets=result.get("totalTargets"),
            rubricNotes=None if status == "correct" else _serialize_json({k: v for k, v in result.items() if k not in {"status", "score", "matchedTargets", "totalTargets"}}),
        ),
    )


def evaluate_deterministically(payload: ActivityFeedbackRequest) -> ActivityFeedbackArtifact | None:
    component = _extract_component(payload)
    evaluators = (
        _evaluate_single_select,
        _evaluate_multi_select,
        _evaluate_ordered_sequence,
        _evaluate_short_answer,
        _evaluate_chess_widget,
        _evaluate_math_symbolic_widget,
        _evaluate_graphing_widget,
        _evaluate_map_widget,
    )
    for evaluator in evaluators:
        result = evaluator(payload, component)
        if result is not None:
            return result
    return None


def _serialize_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True)


class ActivityFeedbackSkill(StructuredOutputSkill):
    name = "activity_feedback"
    input_model = ActivityFeedbackRequest
    output_model = ActivityFeedbackArtifact
    policy = ExecutionPolicy(
        skill_name="activity_feedback",
        skill_version="2026-04-09",
        task_kind="evaluation",
        temperature=0.0,
        max_tokens=1200,
    )

    def build_user_prompt(self, payload: ActivityFeedbackRequest, context) -> str:
        component = _extract_component(payload)
        widget = _extract_widget(payload, component)
        activity_title = payload.activitySpec.title if payload.activitySpec else None
        component_prompt = getattr(component, "prompt", None)
        expected_answer = _extract_expected_answer(component, payload)

        lines = [
            "## Runtime feedback request",
            f"Component ID: {payload.componentId}",
            f"Component type: {payload.componentType}",
        ]
        if widget is not None:
            lines.append(f"Widget engine kind: {widget.engineKind}")
            lines.append(f"Widget surface kind: {widget.surfaceKind}")
        if payload.activityId:
            lines.append(f"Activity ID: {payload.activityId}")
        if activity_title:
            lines.append(f"Activity title: {activity_title}")
        if component_prompt:
            lines.append(f"Component prompt: {component_prompt}")

        lines.extend(
            [
                "",
                "Learner response:",
                _serialize_json(payload.learnerResponse),
                "",
                "Expected answer / answer key:",
                _serialize_json(expected_answer),
            ]
        )

        if component is not None:
            lines.extend(
                [
                    "",
                    "Component config:",
                    _serialize_json(component.model_dump(mode="json", exclude_none=True)),
                ]
            )

        if payload.activitySpec is not None:
            lines.extend(
                [
                    "",
                    f"Activity purpose: {payload.activitySpec.purpose}",
                    f"Activity kind: {payload.activitySpec.activityKind}",
                ]
            )

        lines.extend(
            [
                "",
                "Attempt metadata:",
                _serialize_json(payload.attemptMetadata.model_dump(mode="json", exclude_none=True)),
                "",
                "Return only the activity feedback artifact.",
            ]
        )
        return "\n".join(lines)

    def execute(self, engine, payload: ActivityFeedbackRequest, context) -> SkillExecutionResult:
        preview = self.build_prompt_preview(payload, context)
        widget = _extract_widget(payload, _extract_component(payload))
        deterministic_result = evaluate_deterministically(payload)
        if deterministic_result is not None:
            lineage = ExecutionLineage(
                operation_name=context.operation_name,
                skill_name=self.name,
                skill_version=self.policy.skill_version,
                provider="deterministic",
                model="rule-evaluator",
            )
            trace = ExecutionTrace(
                request_id=context.request_id,
                operation_name=context.operation_name,
                allowed_tools=[],
                prompt_preview=preview,
                request_envelope=OperationEnvelope(
                    input=payload.model_dump(mode="json"),
                    app_context=context.app_context,
                    presentation_context=context.presentation_context,
                    user_authored_context=context.user_authored_context,
                    request_id=context.request_id,
                ),
                agent_trace={
                    "evaluation_method": "deterministic",
                    "component_id": payload.componentId,
                    "component_type": payload.componentType,
                    "widget_engine_kind": widget.engineKind if widget is not None else None,
                    "status": deterministic_result.status,
                },
            )
            return SkillExecutionResult(
                artifact=deterministic_result,
                lineage=lineage,
                trace=trace,
            )

        artifact, lineage, trace = engine.run_structured_output(
            skill=self,
            payload=payload,
            context=context,
        )
        trace.agent_trace = {
            "evaluation_method": "llm",
            "component_id": payload.componentId,
            "component_type": payload.componentType,
            "widget_engine_kind": widget.engineKind if widget is not None else None,
            "deterministic_fallback_reason": "no deterministic evaluator matched this response",
        }
        return SkillExecutionResult(
            artifact=artifact,
            lineage=lineage,
            trace=trace,
        )
