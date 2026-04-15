from __future__ import annotations

from learning_core.contracts.source_interpret import SourceInterpretationArtifact
from learning_core.response_types.base import ResponseTypeDefinition


SOURCE_INTERPRETATION_RESPONSE_TYPE = ResponseTypeDefinition(
    name="source_interpretation",
    artifact_model=SourceInterpretationArtifact,
    description="Structured source interpretation artifact.",
)
