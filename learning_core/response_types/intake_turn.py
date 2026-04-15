from __future__ import annotations

from learning_core.contracts.curriculum import CurriculumIntakeArtifact
from learning_core.response_types.base import ResponseTypeDefinition


INTAKE_TURN_RESPONSE_TYPE = ResponseTypeDefinition(
    name="intake_turn",
    artifact_model=CurriculumIntakeArtifact,
    description="Interactive intake turn output with captured requirements state.",
)
