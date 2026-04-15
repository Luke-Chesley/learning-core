from __future__ import annotations

from learning_core.contracts.curriculum import CurriculumUpdateProposalArtifact
from learning_core.response_types.base import ResponseTypeDefinition


PROPOSAL_RESPONSE_TYPE = ResponseTypeDefinition(
    name="proposal",
    artifact_model=CurriculumUpdateProposalArtifact,
    description="Bounded proposal artifact for durable curriculum updates.",
)
