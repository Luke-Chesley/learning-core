from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4

from learning_core.contracts.operation import AppContext, PresentationContext, UserAuthoredContext


@dataclass(frozen=True)
class RuntimeContext:
    operation_name: str
    request_id: str
    started_at: str
    app_context: AppContext
    presentation_context: PresentationContext
    user_authored_context: UserAuthoredContext

    @classmethod
    def create(
        cls,
        *,
        operation_name: str,
        request_id: str | None = None,
        app_context: AppContext,
        presentation_context: PresentationContext,
        user_authored_context: UserAuthoredContext,
    ) -> "RuntimeContext":
        return cls(
            operation_name=operation_name,
            request_id=request_id or str(uuid4()),
            started_at=datetime.now(timezone.utc).isoformat(),
            app_context=app_context,
            presentation_context=presentation_context,
            user_authored_context=user_authored_context,
        )
