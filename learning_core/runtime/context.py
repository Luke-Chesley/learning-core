from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4


@dataclass(frozen=True)
class RuntimeContext:
    operation_name: str
    request_id: str
    started_at: str

    @classmethod
    def create(cls, operation_name: str, request_id: str | None = None) -> "RuntimeContext":
        return cls(
            operation_name=operation_name,
            request_id=request_id or str(uuid4()),
            started_at=datetime.now(timezone.utc).isoformat(),
        )

