from __future__ import annotations

from learning_core.contracts.curriculum import CurriculumRevisionTurn
from learning_core.response_types.base import ResponseTypeDefinition


CURRICULUM_REVISION_TURN_RESPONSE_TYPE = ResponseTypeDefinition(
    name="curriculum_artifact_revision",
    artifact_model=CurriculumRevisionTurn,
    description="Revision turn containing either a clarification or a revised curriculum artifact.",
)
