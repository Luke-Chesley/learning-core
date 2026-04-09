from __future__ import annotations

from typing import Any, Literal

from pydantic import Field

from learning_core.contracts.base import StrictModel


class AppContext(StrictModel):
    product: str
    surface: str
    organization_id: str | None = None
    learner_id: str | None = None
    lesson_session_id: str | None = None
    plan_item_ids: list[str] = Field(default_factory=list)
    workflow_mode: str | None = None
    request_origin: Literal["ui_action", "server_action", "background_job", "api", "copilot"] = "api"
    debug: bool = False


class PresentationContext(StrictModel):
    audience: Literal["parent", "teacher", "learner", "internal"] = "internal"
    tone: Literal["practical", "concise", "supportive", "neutral"] = "practical"
    ui_density: Literal["compact", "normal", "detailed"] = "normal"
    display_intent: Literal["preview", "final", "review", "edit"] = "final"
    should_return_prompt_preview: bool = False


class UserAuthoredContext(StrictModel):
    note: str | None = None
    teacher_note: str | None = None
    parent_goal: str | None = None
    special_constraints: list[str] = Field(default_factory=list)
    custom_instruction: str | None = None
    avoidances: list[str] = Field(default_factory=list)


class OperationEnvelope(StrictModel):
    input: dict[str, Any]
    app_context: AppContext
    presentation_context: PresentationContext = Field(default_factory=PresentationContext)
    user_authored_context: UserAuthoredContext = Field(default_factory=UserAuthoredContext)
    request_id: str | None = None
