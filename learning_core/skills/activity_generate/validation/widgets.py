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
from learning_core.skills.activity_generate.packs.base import Pack, PackValidationContext


def _validate_widget_runtime_semantics(
    *,
    artifact: ActivityArtifact,
    component_index: int,
    component,
    widget: InteractiveWidgetPayload,
    first_interactive_index: int | None,
    total_interactive_count: int,
) -> tuple[list[str], list[str]]:
    """Validate widget runtime semantics. Returns (hard_errors, soft_warnings)."""
    hard_errors: list[str] = []
    soft_warnings: list[str] = []
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

    # --- Hard errors: true semantic invalidity ---

    if not prompt and not instruction_text:
        hard_errors.append(
            f'Interactive widget "{component.id}" must include learner-facing instructions in prompt or widget.instructionText.'
        )

    if accepts_input and component.required is False:
        hard_errors.append(
            f'Interactive widget "{component.id}" accepts input and should remain required for coherent runtime behavior.'
        )

    if widget.feedback.mode == "explicit_submit" and widget.interaction.submissionMode == "immediate":
        hard_errors.append(
            f'Interactive widget "{component.id}" uses explicit_submit feedback without an explicit_submit interaction mode.'
        )

    if not widget_allows_reset(widget) and getattr(widget.interaction, "allowReset", False):
        hard_errors.append(
            f'Interactive widget "{component.id}" leaves allowReset enabled while resetPolicy disallows reset.'
        )

    if caption and caption == prompt:
        hard_errors.append(
            f'Interactive widget "{component.id}" should not duplicate the prompt verbatim in widget.caption.'
        )

    # --- Soft warnings: composition/layout preferences ---

    if role == "primary" and first_interactive_index is not None and component_index != first_interactive_index:
        soft_warnings.append(
            f'Interactive widget "{component.id}" is marked primary but is not the first interactive component in the activity.'
        )

    if accepts_input and not primary_input_widgets:
        soft_warnings.append("At least one learner-input widget should be marked primary in the activity composition.")

    if role == "supporting" and accepts_input and total_interactive_count <= 1:
        soft_warnings.append(
            f'Interactive widget "{component.id}" is marked supporting but is the only interactive evidence in the activity.'
        )

    return hard_errors, soft_warnings


def normalize_and_validate_widget_activity(
    artifact: ActivityArtifact,
    active_packs: list[Pack] | None = None,
    pack_validation_contexts: dict[str, PackValidationContext] | None = None,
) -> tuple[ActivityArtifact, list[str], list[str]]:
    """Validate and normalize widget activity.

    Returns (normalized_artifact, hard_errors, soft_warnings).
    Hard errors must be fixed. Soft warnings are included in repair prompts
    but do not cause hard failure on their own.
    """
    normalized = artifact.model_copy(deep=True)
    hard_errors: list[str] = []
    soft_warnings: list[str] = []
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

        widget_hard, widget_soft = _validate_widget_runtime_semantics(
            artifact=normalized,
            component_index=index,
            component=component,
            widget=component.widget,
            first_interactive_index=first_interactive_index,
            total_interactive_count=len(interactive_indexes),
        )
        hard_errors.extend(widget_hard)
        soft_warnings.extend(widget_soft)

    # Run pack-specific validators
    for pack in (active_packs or []):
        validation_context = (pack_validation_contexts or {}).get(pack.name)
        for validator in pack.validators():
            normalized, pack_hard, pack_soft = validator.normalize_and_validate(normalized, validation_context)
            hard_errors.extend(pack_hard)
            soft_warnings.extend(pack_soft)

    return normalized, hard_errors, soft_warnings
