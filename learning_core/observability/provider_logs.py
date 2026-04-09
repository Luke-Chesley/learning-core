from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _log_root() -> Path:
    override = (os.getenv("LEARNING_CORE_LOG_DIR") or "").strip()
    if override:
        return Path(override).expanduser()
    return _repo_root() / "logs"


def _daily_dir(now: datetime) -> Path:
    day_dir = _log_root() / now.strftime("%Y-%m-%d")
    day_dir.mkdir(parents=True, exist_ok=True)
    return day_dir


def _serialize(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return {str(key): _serialize(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_serialize(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value

    content = getattr(value, "content", None)
    response_metadata = getattr(value, "response_metadata", None)
    additional_kwargs = getattr(value, "additional_kwargs", None)
    tool_calls = getattr(value, "tool_calls", None)
    invalid_tool_calls = getattr(value, "invalid_tool_calls", None)
    usage_metadata = getattr(value, "usage_metadata", None)

    if any(item is not None for item in (content, response_metadata, additional_kwargs, tool_calls, invalid_tool_calls, usage_metadata)):
        return {
            "type": value.__class__.__name__,
            "content": _serialize(content),
            "response_metadata": _serialize(response_metadata),
            "additional_kwargs": _serialize(additional_kwargs),
            "tool_calls": _serialize(tool_calls),
            "invalid_tool_calls": _serialize(invalid_tool_calls),
            "usage_metadata": _serialize(usage_metadata),
        }

    return {
        "type": value.__class__.__name__,
        "repr": repr(value),
    }


def _build_filename(now: datetime) -> str:
    base = now.strftime("%Y-%m-%dT%H-%M-%S.%f%z")
    return f"{base}.log"


def write_provider_exchange_log(*, request: dict[str, Any], response: dict[str, Any]) -> Path:
    now = datetime.now().astimezone()
    day_dir = _daily_dir(now)
    path = day_dir / _build_filename(now)

    suffix = 1
    while path.exists():
        path = day_dir / f"{now.strftime('%Y-%m-%dT%H-%M-%S.%f%z')}__{suffix}.log"
        suffix += 1

    body = "\n".join(
        [
            "REQUEST",
            "_" * 80,
            json.dumps(_serialize(request), indent=2, ensure_ascii=False),
            "",
            "RESPONSE",
            "_" * 80,
            json.dumps(_serialize(response), indent=2, ensure_ascii=False),
            "",
        ]
    )
    path.write_text(body, encoding="utf-8")
    return path
