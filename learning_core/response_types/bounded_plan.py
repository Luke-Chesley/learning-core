from __future__ import annotations

from learning_core.contracts.bounded_plan import BoundedPlanArtifact
from learning_core.response_types.base import ResponseTypeDefinition


BOUNDED_PLAN_RESPONSE_TYPE = ResponseTypeDefinition(
    name="bounded_plan",
    artifact_model=BoundedPlanArtifact,
    description="Bounded planning artifact.",
)
