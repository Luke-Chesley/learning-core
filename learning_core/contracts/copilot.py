from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import Field

from learning_core.contracts.base import StrictModel


class CopilotChatMessage(StrictModel):
    role: Literal["user", "assistant", "system"]
    content: str


class CopilotChatContext(StrictModel):
    learnerId: str | None = None
    learnerName: str | None = None
    curriculumSourceId: str | None = None
    lessonId: str | None = None
    standardIds: list[str] = Field(default_factory=list)
    goalIds: list[str] = Field(default_factory=list)
    curriculumSnapshot: dict[str, Any] | None = None
    dailyWorkspaceSnapshot: dict[str, Any] | None = None
    weeklyPlanningSnapshot: dict[str, Any] | None = None
    feedbackNotes: list[str] = Field(default_factory=list)
    recentOutcomes: list[dict[str, Any]] = Field(default_factory=list)


class CopilotChatRequest(StrictModel):
    messages: list[CopilotChatMessage] = Field(default_factory=list)
    context: CopilotChatContext | None = None


class CopilotActionTarget(StrictModel):
    entityType: Literal[
        "weekly_route_item",
        "planning_day",
        "today_lesson",
        "lesson_session",
        "tracking_note",
    ]
    entityId: str | None = None
    secondaryEntityId: str | None = None
    date: str | None = None


class PlanningRouteMovePayload(StrictModel):
    weeklyRouteId: str
    weeklyRouteItemId: str
    currentDate: str | None = None
    targetDate: str | None = None
    targetIndex: int = 0
    reason: str


class GenerateTodayLessonPayload(StrictModel):
    date: str
    slotId: str | None = None
    reason: str


class TrackingRecordNotePayload(StrictModel):
    title: str | None = None
    body: str
    noteType: Literal["general", "mastery", "adaptation_signal"] = "general"
    planItemId: str | None = None
    lessonSessionId: str | None = None


class CopilotActionBase(StrictModel):
    id: str
    label: str
    description: str
    rationale: str | None = None
    confidence: Literal["low", "medium", "high"] | None = None
    requiresApproval: bool = True
    target: CopilotActionTarget | None = None


class PlanningAdjustDayLoadAction(CopilotActionBase):
    kind: Literal["planning.adjust_day_load"]
    payload: PlanningRouteMovePayload


class PlanningDeferOrMoveItemAction(CopilotActionBase):
    kind: Literal["planning.defer_or_move_item"]
    payload: PlanningRouteMovePayload


class PlanningGenerateTodayLessonAction(CopilotActionBase):
    kind: Literal["planning.generate_today_lesson"]
    payload: GenerateTodayLessonPayload


class TrackingRecordNoteAction(CopilotActionBase):
    kind: Literal["tracking.record_note"]
    payload: TrackingRecordNotePayload


CopilotAction = Annotated[
    PlanningAdjustDayLoadAction
    | PlanningDeferOrMoveItemAction
    | PlanningGenerateTodayLessonAction
    | TrackingRecordNoteAction,
    Field(discriminator="kind"),
]


class CopilotChatArtifact(StrictModel):
    answer: str
    actions: list[CopilotAction] = Field(default_factory=list)
