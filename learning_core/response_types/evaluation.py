from __future__ import annotations

from learning_core.contracts.evaluation import EvaluationArtifact
from learning_core.response_types.base import ResponseTypeDefinition


EVALUATION_RESPONSE_TYPE = ResponseTypeDefinition(
    name="evaluation",
    artifact_model=EvaluationArtifact,
    description="Evaluation artifact with evidence, rating, and next actions.",
)
