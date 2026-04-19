from __future__ import annotations

from learning_core.contracts.launch_plan import LaunchPlanArtifact
from learning_core.response_types.base import ResponseTypeDefinition


LAUNCH_PLAN_ARTIFACT_RESPONSE_TYPE = ResponseTypeDefinition(
    name="launch_plan_artifact",
    artifact_model=LaunchPlanArtifact,
    description="Bounded launch-plan artifact for the opening curriculum slice.",
)
