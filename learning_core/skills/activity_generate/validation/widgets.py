from __future__ import annotations

from learning_core.contracts.activity import ActivityArtifact
from learning_core.contracts.widgets import widget_accepts_input
from learning_core.skills.activity_generate.validation.chess import (
    normalize_chess_widget,
    validate_chess_widget,
)


def normalize_and_validate_widget_activity(
    artifact: ActivityArtifact,
) -> tuple[ActivityArtifact, list[str]]:
    normalized = artifact.model_copy(deep=True)
    errors: list[str] = []

    for component in normalized.components:
        if component.type != "interactive_widget":
            continue

        prompt = (component.prompt or "").strip()
        if not prompt:
            errors.append(f'Interactive widget "{component.id}" must include a learner-facing prompt.')

        if widget_accepts_input(component.widget) and component.required is False:
            errors.append(
                f'Interactive widget "{component.id}" accepts input and should remain required for coherent runtime behavior.'
            )

        if component.widget.engineKind == "chess":
            try:
                component.widget = normalize_chess_widget(component.widget)
            except ValueError as error:
                errors.append(f'Interactive widget "{component.id}" has invalid chess state: {error}')
                continue
            errors.extend(validate_chess_widget(component, component.widget))

    return normalized, errors
