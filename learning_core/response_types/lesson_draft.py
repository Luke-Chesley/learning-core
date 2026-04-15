from __future__ import annotations

from learning_core.contracts.session_plan import SessionPlanArtifact
from learning_core.response_types.base import ResponseTypeDefinition


LESSON_DRAFT_RESPONSE_TYPE = ResponseTypeDefinition(
    name="lesson_draft",
    artifact_model=SessionPlanArtifact,
    description="Structured lesson draft output for bounded day generation.",
)
