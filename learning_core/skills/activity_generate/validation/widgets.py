from __future__ import annotations

from learning_core.contracts.activity import ActivityArtifact, INTERACTIVE_COMPONENT_TYPES
from learning_core.contracts.widgets import (
    InteractiveWidgetPayload,
    widget_accepts_input,
    widget_allows_reset,
    widget_caption,
    widget_instruction_text,
    widget_surface_role,
)
from learning_core.skills.activity_generate.validation.chess import (
    normalize_chess_widget,
    validate_chess_widget,
)


def _validate_widget_runtime_semantics(
    *,
    artifact: ActivityArtifact,
    component_index: int,
    component,
    widget: InteractiveWidgetPayload,
    first_interactive_index: int | None,
    total_interactive_count: int,
) -> list[str]:
    errors: list[str] = []
    prompt = (component.prompt or "").strip()
    instruction_text = (widget_instruction_text(widget) or "").strip()
    caption = (widget_caption(widget) or "").strip()
    role = widget_surface_role(widget)
    accepts_input = widget_accepts_input(widget)
    primary_input_widgets = [
        candidate
        for candidate in artifact.components
        if candidate.type == "interactive_widget"
        and widget_accepts_input(candidate.widget)
        and widget_surface_role(candidate.widget) == "primary"
    ]

    if not prompt and not instruction_text:
        errors.append(
            f'Interactive widget "{component.id}" must include learner-facing instructions in prompt or widget.instructionText.'
        )

    if accepts_input and component.required is False:
        errors.append(
            f'Interactive widget "{component.id}" accepts input and should remain required for coherent runtime behavior.'
        )

    if widget.feedback.mode == "explicit_submit" and widget.interaction.submissionMode == "immediate":
        errors.append(
            f'Interactive widget "{component.id}" uses explicit_submit feedback without an explicit_submit interaction mode.'
        )

    if role == "primary" and first_interactive_index is not None and component_index != first_interactive_index:
        errors.append(
            f'Interactive widget "{component.id}" is marked primary but is not the first interactive component in the activity.'
        )

    if accepts_input and not primary_input_widgets:
        errors.append("At least one learner-input widget must be marked primary in the activity composition.")

    if role == "supporting" and accepts_input and total_interactive_count <= 1:
        errors.append(
            f'Interactive widget "{component.id}" is marked supporting but is the only interactive evidence in the activity.'
        )

    if not widget_allows_reset(widget) and getattr(widget.interaction, "allowReset", False):
        errors.append(
            f'Interactive widget "{component.id}" leaves allowReset enabled while resetPolicy disallows reset.'
        )

    if caption and caption == prompt:
        errors.append(
            f'Interactive widget "{component.id}" should not duplicate the prompt verbatim in widget.caption.'
        )

    return errors


def normalize_and_validate_widget_activity(
    artifact: ActivityArtifact,
) -> tuple[ActivityArtifact, list[str]]:
    normalized = artifact.model_copy(deep=True)
    errors: list[str] = []
    interactive_indexes: list[int] = []
    for index, component in enumerate(normalized.components):
        if component.type == "interactive_widget":
            if widget_accepts_input(component.widget):
                interactive_indexes.append(index)
            continue
        if component.type in INTERACTIVE_COMPONENT_TYPES:
            interactive_indexes.append(index)
    first_interactive_index = interactive_indexes[0] if interactive_indexes else None

    for index, component in enumerate(normalized.components):
        if component.type != "interactive_widget":
            continue

        errors.extend(
            _validate_widget_runtime_semantics(
                artifact=normalized,
                component_index=index,
                component=component,
                widget=component.widget,
                first_interactive_index=first_interactive_index,
                total_interactive_count=len(interactive_indexes),
            )
        )

        if component.widget.engineKind == "chess":
            try:
                component.widget = normalize_chess_widget(component.widget)
            except ValueError as error:
                errors.append(f'Interactive widget "{component.id}" has invalid chess state: {error}')
                continue
            errors.extend(validate_chess_widget(normalized, component, component.widget))

    return normalized, errors
