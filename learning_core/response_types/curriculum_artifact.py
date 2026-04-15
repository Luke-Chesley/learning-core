from __future__ import annotations

from learning_core.contracts.curriculum import CurriculumArtifact
from learning_core.response_types.base import ResponseTypeDefinition


CURRICULUM_ARTIFACT_RESPONSE_TYPE = ResponseTypeDefinition(
    name="curriculum_artifact",
    artifact_model=CurriculumArtifact,
    description="Long-horizon curriculum artifact.",
)
