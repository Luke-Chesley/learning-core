from __future__ import annotations

from learning_core.contracts.progression import ProgressionArtifact
from learning_core.response_types.base import ResponseTypeDefinition


PROGRESSION_ARTIFACT_RESPONSE_TYPE = ResponseTypeDefinition(
    name="progression_artifact",
    artifact_model=ProgressionArtifact,
    description="Progression graph artifact.",
)
