from __future__ import annotations

from learning_core.contracts.widget_transition import WidgetTransitionArtifact
from learning_core.response_types.base import ResponseTypeDefinition


WIDGET_TRANSITION_RESPONSE_TYPE = ResponseTypeDefinition(
    name="widget_transition",
    artifact_model=WidgetTransitionArtifact,
    description="Deterministic widget transition artifact.",
)
