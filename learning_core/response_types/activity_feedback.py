from __future__ import annotations

from learning_core.contracts.activity_feedback import ActivityFeedbackArtifact
from learning_core.response_types.base import ResponseTypeDefinition


ACTIVITY_FEEDBACK_RESPONSE_TYPE = ResponseTypeDefinition(
    name="activity_feedback",
    artifact_model=ActivityFeedbackArtifact,
    description="Component feedback artifact for activity evaluation.",
)
