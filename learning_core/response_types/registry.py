from __future__ import annotations

from learning_core.response_types.activity_feedback import ACTIVITY_FEEDBACK_RESPONSE_TYPE
from learning_core.response_types.activity_spec import ACTIVITY_SPEC_RESPONSE_TYPE
from learning_core.response_types.base import ResponseTypeDefinition
from learning_core.response_types.curriculum_artifact import CURRICULUM_ARTIFACT_RESPONSE_TYPE
from learning_core.response_types.curriculum_revision_turn import CURRICULUM_REVISION_TURN_RESPONSE_TYPE
from learning_core.response_types.evaluation import EVALUATION_RESPONSE_TYPE
from learning_core.response_types.intake_turn import INTAKE_TURN_RESPONSE_TYPE
from learning_core.response_types.lesson_draft import LESSON_DRAFT_RESPONSE_TYPE
from learning_core.response_types.progression_artifact import PROGRESSION_ARTIFACT_RESPONSE_TYPE
from learning_core.response_types.proposal import PROPOSAL_RESPONSE_TYPE
from learning_core.response_types.source_interpretation import SOURCE_INTERPRETATION_RESPONSE_TYPE
from learning_core.response_types.summary import SUMMARY_RESPONSE_TYPE
from learning_core.response_types.widget_transition import WIDGET_TRANSITION_RESPONSE_TYPE


RESPONSE_TYPE_REGISTRY: dict[str, ResponseTypeDefinition] = {
    definition.name: definition
    for definition in (
        ACTIVITY_FEEDBACK_RESPONSE_TYPE,
        ACTIVITY_SPEC_RESPONSE_TYPE,
        CURRICULUM_ARTIFACT_RESPONSE_TYPE,
        CURRICULUM_REVISION_TURN_RESPONSE_TYPE,
        EVALUATION_RESPONSE_TYPE,
        INTAKE_TURN_RESPONSE_TYPE,
        LESSON_DRAFT_RESPONSE_TYPE,
        PROGRESSION_ARTIFACT_RESPONSE_TYPE,
        PROPOSAL_RESPONSE_TYPE,
        SOURCE_INTERPRETATION_RESPONSE_TYPE,
        SUMMARY_RESPONSE_TYPE,
        WIDGET_TRANSITION_RESPONSE_TYPE,
    )
}


def get_response_type(name: str) -> ResponseTypeDefinition:
    return RESPONSE_TYPE_REGISTRY[name]
