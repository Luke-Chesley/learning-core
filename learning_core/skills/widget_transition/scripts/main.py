from __future__ import annotations

from typing import Any

from learning_core.contracts.activity_feedback import ActivityFeedbackArtifact, FeedbackScoring
from learning_core.contracts.operation import OperationEnvelope
from learning_core.contracts.widget_transition import WidgetTransitionArtifact, WidgetTransitionRequest
from learning_core.observability.traces import ExecutionLineage, ExecutionTrace, PromptPreview
from learning_core.runtime.policy import ExecutionPolicy
from learning_core.runtime.skill import SkillExecutionResult
from learning_core.skills.base import StructuredOutputSkill
from learning_core.domain.chess_engine import apply_move, evaluate_move, legal_targets


def _prompt_preview(payload: WidgetTransitionRequest) -> PromptPreview:
    return PromptPreview(
        system_prompt="Widget transitions are handled deterministically.",
        user_prompt=(
            f"Component ID: {payload.componentId}\n"
            f"Component type: {payload.componentType}\n"
            f"Widget engine kind: {payload.widget.engineKind}\n"
            f"Learner action: {payload.learnerAction.model_dump(mode='json', exclude_none=True)}"
        ),
    )


def _feedback_from_chess_result(
    *,
    payload: WidgetTransitionRequest,
    result: dict[str, Any],
) -> ActivityFeedbackArtifact:
    is_correct = result["status"] == "correct"
    return ActivityFeedbackArtifact(
        schemaVersion="1",
        componentId=payload.componentId,
        componentType=payload.componentType,
        widgetEngineKind=payload.widget.engineKind,
        status="correct" if is_correct else "incorrect",
        feedbackMessage=(
            "That move matches the expected move."
            if is_correct
            else "That move does not match the expected move for this position."
        ),
        hint=(
            None
            if is_correct
            else "Look again at the immediate tactical or positional goal in the position."
        ),
        nextStep=(
            None
            if is_correct
            else "Try another move from the same position."
        ),
        confidence=0.99,
        allowRetry=not is_correct,
        evaluationMethod="deterministic",
        scoring=FeedbackScoring(
            score=1.0 if is_correct else 0.0,
            matchedTargets=int(is_correct),
            totalTargets=1,
        ),
    )


def _initial_chess_widget(widget):
    reset_widget = widget.model_copy(deep=True)
    reset_widget.state.fen = widget.state.initialFen or widget.state.fen
    return reset_widget


def _move_response_payload(move_result: dict[str, Any]) -> dict[str, Any]:
    return {
        **move_result["normalizedMove"],
        "fenAfter": move_result["fenAfter"],
    }


def _transition_chess_widget(payload: WidgetTransitionRequest) -> WidgetTransitionArtifact:
    widget = payload.widget
    action = payload.learnerAction

    if widget.interaction.mode != "move_input" and action.type != "reset":
        return WidgetTransitionArtifact(
            schemaVersion="1",
            componentId=payload.componentId,
            componentType=payload.componentType,
            widgetEngineKind=widget.engineKind,
            accepted=False,
            normalizedLearnerAction=action.model_dump(mode="json", exclude_none=True),
            nextResponse=payload.currentResponse,
            canonicalWidget=widget,
            legalTargets=[],
            errorMessage="This board is view-only and does not accept move input.",
        )

    if action.type == "reset":
        if not widget.interaction.allowReset or widget.interaction.resetPolicy == "not_allowed":
            return WidgetTransitionArtifact(
                schemaVersion="1",
                componentId=payload.componentId,
                componentType=payload.componentType,
                widgetEngineKind=widget.engineKind,
                accepted=False,
                normalizedLearnerAction=action.model_dump(mode="json"),
                nextResponse=payload.currentResponse,
                canonicalWidget=widget,
                legalTargets=[],
                errorMessage="Reset is not allowed for this widget.",
            )

        return WidgetTransitionArtifact(
            schemaVersion="1",
            componentId=payload.componentId,
            componentType=payload.componentType,
            widgetEngineKind=widget.engineKind,
            accepted=True,
            normalizedLearnerAction=action.model_dump(mode="json"),
            nextResponse=None,
            canonicalWidget=_initial_chess_widget(widget),
            legalTargets=[],
        )

    if action.type == "select_square":
        targets = legal_targets(widget.state.fen, action.square)
        if not targets:
            return WidgetTransitionArtifact(
                schemaVersion="1",
                componentId=payload.componentId,
                componentType=payload.componentType,
                widgetEngineKind=widget.engineKind,
                accepted=False,
                normalizedLearnerAction=action.model_dump(mode="json"),
                nextResponse=payload.currentResponse,
                canonicalWidget=widget,
                legalTargets=[],
                errorMessage="Select a piece that has a legal move from the current position.",
            )

        return WidgetTransitionArtifact(
            schemaVersion="1",
            componentId=payload.componentId,
            componentType=payload.componentType,
            widgetEngineKind=widget.engineKind,
            accepted=True,
            normalizedLearnerAction=action.model_dump(mode="json"),
            nextResponse=payload.currentResponse,
            canonicalWidget=widget,
            legalTargets=targets,
        )

    move_input = action.move
    if hasattr(move_input, "model_dump"):
        normalized_input = move_input.model_dump(mode="json", exclude_none=True)
        move_input = normalized_input
    if isinstance(move_input, dict):
        normalized_input = dict(move_input)
        if "fromSquare" in normalized_input:
            normalized_input["from"] = normalized_input.pop("fromSquare")
        if "toSquare" in normalized_input:
            normalized_input["to"] = normalized_input.pop("toSquare")
        move_input = normalized_input

    def _without_promotion(candidate: Any) -> Any:
        if not isinstance(candidate, dict) or "promotion" not in candidate:
            return candidate
        fallback = dict(candidate)
        fallback.pop("promotion", None)
        return fallback

    def _candidate_from_square(candidate: Any) -> str | None:
        if not isinstance(candidate, dict):
            return None
        for key in ("from", "fromSquare"):
            value = candidate.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip().lower()
        return None

    try:
        move_result = apply_move(widget.state.fen, move_input)
    except ValueError as error:
        fallback_move_input = _without_promotion(move_input)
        if fallback_move_input is not move_input:
            try:
                move_input = fallback_move_input
                move_result = apply_move(widget.state.fen, move_input)
            except ValueError:
                move_input = fallback_move_input
            else:
                error = None
        if error is not None:
            hinted_legal_targets = []
            from_square = _candidate_from_square(move_input)
            if from_square:
                hinted_legal_targets = legal_targets(widget.state.fen, from_square)
            return WidgetTransitionArtifact(
                schemaVersion="1",
                componentId=payload.componentId,
                componentType=payload.componentType,
                widgetEngineKind=widget.engineKind,
                accepted=False,
                normalizedLearnerAction=action.model_dump(mode="json", exclude_none=True),
                nextResponse=payload.currentResponse,
                canonicalWidget=widget,
                legalTargets=hinted_legal_targets,
                errorMessage=str(error),
            )

    next_widget = widget.model_copy(deep=True)
    next_widget.state.fen = move_result["fenAfter"]
    next_response = _move_response_payload(move_result)

    immediate_feedback = None
    if widget.feedback.mode == "immediate" and widget.evaluation.expectedMoves:
        evaluated_move = evaluate_move(widget.state.fen, move_input, widget.evaluation.expectedMoves)
        immediate_feedback = _feedback_from_chess_result(
            payload=payload,
            result=evaluated_move,
        )

        if evaluated_move["status"] != "correct" and widget.interaction.attemptPolicy == "allow_retry":
            return WidgetTransitionArtifact(
                schemaVersion="1",
                componentId=payload.componentId,
                componentType=payload.componentType,
                widgetEngineKind=widget.engineKind,
                accepted=True,
                normalizedLearnerAction=move_result["normalizedMove"],
                nextResponse=None,
                canonicalWidget=_initial_chess_widget(widget),
                legalTargets=[],
                immediateFeedback=immediate_feedback,
            )

    return WidgetTransitionArtifact(
        schemaVersion="1",
        componentId=payload.componentId,
        componentType=payload.componentType,
        widgetEngineKind=widget.engineKind,
        accepted=True,
        normalizedLearnerAction=move_result["normalizedMove"],
        nextResponse=next_response,
        canonicalWidget=next_widget,
        legalTargets=[],
        immediateFeedback=immediate_feedback,
    )


def evaluate_transition(payload: WidgetTransitionRequest) -> WidgetTransitionArtifact:
    if payload.componentType != "interactive_widget":
        return WidgetTransitionArtifact(
            schemaVersion="1",
            componentId=payload.componentId,
            componentType=payload.componentType,
            widgetEngineKind=payload.widget.engineKind,
            accepted=False,
            normalizedLearnerAction=payload.learnerAction.model_dump(mode="json", exclude_none=True),
            nextResponse=payload.currentResponse,
            canonicalWidget=payload.widget,
            legalTargets=[],
            errorMessage="Widget transitions are only supported for interactive_widget components.",
        )

    if payload.widget.engineKind == "chess":
        return _transition_chess_widget(payload)

    return WidgetTransitionArtifact(
        schemaVersion="1",
        componentId=payload.componentId,
        componentType=payload.componentType,
        widgetEngineKind=payload.widget.engineKind,
        accepted=False,
        normalizedLearnerAction=payload.learnerAction.model_dump(mode="json", exclude_none=True),
        nextResponse=payload.currentResponse,
        canonicalWidget=payload.widget,
        legalTargets=[],
        errorMessage=f"Widget transition is not implemented for engine kind '{payload.widget.engineKind}'.",
    )


class WidgetTransitionSkill(StructuredOutputSkill):
    name = "widget_transition"
    input_model = WidgetTransitionRequest
    output_model = WidgetTransitionArtifact
    policy = ExecutionPolicy(
        skill_name="widget_transition",
        skill_version="2026-04-10",
        task_kind="evaluation",
        temperature=0.0,
        max_tokens=800,
    )

    def build_user_prompt(self, payload: WidgetTransitionRequest, context) -> str:
        preview = _prompt_preview(payload)
        return preview.user_prompt

    def execute(self, engine, payload: WidgetTransitionRequest, context) -> SkillExecutionResult:
        artifact = evaluate_transition(payload)
        preview = _prompt_preview(payload)
        lineage = ExecutionLineage(
            operation_name=context.operation_name,
            skill_name=self.name,
            skill_version=self.policy.skill_version,
            provider="deterministic",
            model="widget-transition-engine",
        )
        trace = ExecutionTrace(
            request_id=context.request_id,
            operation_name=context.operation_name,
            allowed_tools=[],
            prompt_preview=preview,
            request_envelope=OperationEnvelope(
                input=payload.model_dump(mode="json", exclude_none=True),
                app_context=context.app_context,
                presentation_context=context.presentation_context,
                user_authored_context=context.user_authored_context,
                request_id=context.request_id,
            ),
            agent_trace={
                "transition_method": "deterministic",
                "component_id": payload.componentId,
                "component_type": payload.componentType,
                "widget_engine_kind": payload.widget.engineKind,
                "accepted": artifact.accepted,
                "action_type": payload.learnerAction.type,
            },
        )
        return SkillExecutionResult(
            artifact=artifact,
            lineage=lineage,
            trace=trace,
        )
