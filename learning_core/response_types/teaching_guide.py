from __future__ import annotations

from learning_core.contracts.teaching_guide import TeachingGuideArtifact
from learning_core.response_types.base import ResponseTypeDefinition


TEACHING_GUIDE_RESPONSE_TYPE = ResponseTypeDefinition(
    name="teaching_guide_artifact",
    artifact_model=TeachingGuideArtifact,
    description="Parent-facing teaching guide for preteach, lesson review, and misconception repair support.",
)
