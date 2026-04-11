from __future__ import annotations

import re

from learning_core.contracts.activity import ActivityArtifact, InteractiveWidgetComponent
from learning_core.contracts.widgets import GraphingWidget, MathSymbolicWidget
from learning_core.skills.activity_generate.packs.base import PackValidationContext, PackValidator

_SOLVE_PATTERNS = (
    re.compile(r"\bsolve\b", re.IGNORECASE),
    re.compile(r"\bsimplify\b", re.IGNORECASE),
    re.compile(r"\bevaluate\b", re.IGNORECASE),
    re.compile(r"\bfind the (?:value|expression|equation)\b", re.IGNORECASE),
    re.compile(r"\benter (?:the|your) (?:answer|expression|equation|solution)\b", re.IGNORECASE),
)

_GRAPH_CENTERED_PATTERNS = (
    re.compile(r"\bplot\b", re.IGNORECASE),
    re.compile(r"\bgraph\b", re.IGNORECASE),
    re.compile(r"\bsketch\b", re.IGNORECASE),
    re.compile(r"\bdraw (?:the|a) (?:line|curve|graph|function)\b", re.IGNORECASE),
)


def _all_visible_text(component: InteractiveWidgetComponent, widget: MathSymbolicWidget | GraphingWidget) -> str:
    return " ".join(
        value.strip()
        for value in [component.prompt or "", widget.instructionText or "", widget.caption or ""]
        if value and value.strip()
    )


def validate_math_symbolic_widget(
    artifact: ActivityArtifact,
    component: InteractiveWidgetComponent,
    widget: MathSymbolicWidget,
) -> tuple[list[str], list[str]]:
    hard_errors: list[str] = []
    soft_warnings: list[str] = []
    prompt = _all_visible_text(component, widget)
    mode = widget.interaction.mode
    has_expected = widget.evaluation.expectedExpression is not None and widget.evaluation.expectedExpression.strip() != ""

    # --- Hard errors ---

    if mode in ("expression_entry", "equation_entry", "step_entry") and not has_expected:
        hard_errors.append(
            f'Interactive widget "{component.id}" expects symbolic input but has no evaluation.expectedExpression.'
        )

    if mode == "view_only" and has_expected:
        hard_errors.append(
            f'Interactive widget "{component.id}" is view_only but still includes evaluation.expectedExpression.'
        )

    if mode in ("expression_entry", "equation_entry", "step_entry") and not widget.state.promptLatex:
        hard_errors.append(
            f'Interactive widget "{component.id}" expects input but has no state.promptLatex to frame the problem.'
        )

    # --- Soft warnings ---

    if mode != "view_only" and widget.display.surfaceRole != "primary":
        soft_warnings.append(
            f'Interactive widget "{component.id}" accepts expression input but display.surfaceRole is not "primary".'
        )

    if any(pattern.search(prompt) for pattern in _SOLVE_PATTERNS):
        if mode == "view_only":
            soft_warnings.append(
                f'Interactive widget "{component.id}" appears in a solve/evaluate context but does not accept input.'
            )

    return hard_errors, soft_warnings


def validate_graphing_widget(
    artifact: ActivityArtifact,
    component: InteractiveWidgetComponent,
    widget: GraphingWidget,
) -> tuple[list[str], list[str]]:
    hard_errors: list[str] = []
    soft_warnings: list[str] = []
    prompt = _all_visible_text(component, widget)
    mode = widget.interaction.mode
    has_expected = (
        widget.evaluation.expectedGraphDescription is not None
        and widget.evaluation.expectedGraphDescription.strip() != ""
    )

    # --- Hard errors ---

    if mode in ("plot_point", "plot_curve", "analyze_graph") and not has_expected:
        hard_errors.append(
            f'Interactive widget "{component.id}" expects graph input but has no evaluation.expectedGraphDescription.'
        )

    if mode == "view_only" and has_expected:
        hard_errors.append(
            f'Interactive widget "{component.id}" is view_only but still includes evaluation.expectedGraphDescription.'
        )

    # --- Soft warnings ---

    if mode != "view_only" and widget.display.surfaceRole != "primary":
        soft_warnings.append(
            f'Interactive widget "{component.id}" accepts graph input but display.surfaceRole is not "primary".'
        )

    if any(pattern.search(prompt) for pattern in _GRAPH_CENTERED_PATTERNS):
        if mode == "view_only":
            soft_warnings.append(
                f'Interactive widget "{component.id}" appears in a graph-centered context but does not accept input.'
            )

    return hard_errors, soft_warnings


class MathValidator(PackValidator):
    def normalize_and_validate(
        self,
        artifact: ActivityArtifact,
        validation_context: PackValidationContext | None = None,
    ) -> tuple[ActivityArtifact, list[str], list[str]]:
        normalized = artifact.model_copy(deep=True)
        hard_errors: list[str] = []
        soft_warnings: list[str] = []

        for component in normalized.components:
            if component.type != "interactive_widget":
                continue

            if component.widget.engineKind == "math_symbolic":
                widget_hard, widget_soft = validate_math_symbolic_widget(normalized, component, component.widget)
                hard_errors.extend(widget_hard)
                soft_warnings.extend(widget_soft)
            elif component.widget.engineKind == "graphing":
                widget_hard, widget_soft = validate_graphing_widget(normalized, component, component.widget)
                hard_errors.extend(widget_hard)
                soft_warnings.extend(widget_soft)

        return normalized, hard_errors, soft_warnings
