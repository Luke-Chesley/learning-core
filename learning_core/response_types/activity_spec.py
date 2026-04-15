from __future__ import annotations

from learning_core.contracts.activity import ActivityArtifact
from learning_core.response_types.base import ResponseTypeDefinition


ACTIVITY_SPEC_RESPONSE_TYPE = ResponseTypeDefinition(
    name="activity_spec",
    artifact_model=ActivityArtifact,
    description="Structured activity specification output.",
)
