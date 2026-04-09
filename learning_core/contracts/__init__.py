from learning_core.contracts.activity import ActivityArtifact, ActivityGenerationInput
from learning_core.contracts.copilot import CopilotChatArtifact, CopilotChatContext, CopilotChatRequest
from learning_core.contracts.operation import (
    AppContext,
    OperationEnvelope,
    PresentationContext,
    UserAuthoredContext,
)
from learning_core.contracts.responses import (
    OperationDescriptor,
    OperationExecuteResponse,
    OperationPromptPreviewResponse,
)
from learning_core.contracts.curriculum import (
    CurriculumArtifact,
    CurriculumIntakeArtifact,
    CurriculumGenerationRequest,
    CurriculumRevisionTurn,
    CurriculumRevisionRequest,
    CurriculumUpdateProposalArtifact,
    CurriculumUpdateProposalRequest,
)
from learning_core.contracts.evaluation import EvaluationArtifact, SessionEvaluationRequest
from learning_core.contracts.lesson_draft import LESSON_SHAPE_VALUES, LessonShape, StructuredLessonDraft
from learning_core.contracts.progression import (
    ProgressionArtifact,
    ProgressionGenerationRequest,
    ProgressionRevisionRequest,
)
from learning_core.contracts.session_plan import SessionPlanArtifact, SessionPlanGenerationRequest

__all__ = [
    "ActivityArtifact",
    "ActivityGenerationInput",
    "AppContext",
    "CopilotChatArtifact",
    "CopilotChatContext",
    "CopilotChatRequest",
    "CurriculumArtifact",
    "CurriculumIntakeArtifact",
    "CurriculumGenerationRequest",
    "CurriculumRevisionRequest",
    "CurriculumRevisionTurn",
    "CurriculumUpdateProposalArtifact",
    "CurriculumUpdateProposalRequest",
    "EvaluationArtifact",
    "LESSON_SHAPE_VALUES",
    "LessonShape",
    "OperationDescriptor",
    "OperationEnvelope",
    "OperationExecuteResponse",
    "OperationPromptPreviewResponse",
    "PresentationContext",
    "ProgressionArtifact",
    "ProgressionGenerationRequest",
    "ProgressionRevisionRequest",
    "SessionEvaluationRequest",
    "SessionPlanArtifact",
    "SessionPlanGenerationRequest",
    "StructuredLessonDraft",
    "UserAuthoredContext",
]
