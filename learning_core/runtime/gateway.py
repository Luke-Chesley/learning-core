from __future__ import annotations

import json
import re
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any

from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage, SystemMessage
from pydantic import BaseModel

from learning_core.runtime.errors import ProviderExecutionError
from learning_core.runtime.providers import build_model_runtime

FAST_TASKS = {"standards.suggest", "text.summarize", "curriculum.title"}
CHAT_TASKS = {"chat.answer", "curriculum.intake"}


class GatewayUsage(BaseModel):
    prompt_tokens: int | None = None
    completion_tokens: int | None = None


class GatewayCompletionResponse(BaseModel):
    content: str
    provider_id: str
    model_id: str
    usage: GatewayUsage | None = None


class GatewayJsonResponse(GatewayCompletionResponse):
    parsed: Any | None = None


@dataclass(frozen=True)
class GatewayRequest:
    task_name: str
    messages: list[dict[str, str]]
    system_prompt: str | None = None
    temperature: float | None = None
    max_tokens: int | None = None
    model: str | None = None


def _task_kind(task_name: str) -> str:
    if task_name in CHAT_TASKS:
        return "chat"
    if task_name in FAST_TASKS:
        return "fast"
    return "generation"


def _normalize_messages(messages: list[dict[str, str]], system_prompt: str | None) -> list[Any]:
    normalized: list[Any] = []
    if system_prompt:
        normalized.append(SystemMessage(content=system_prompt))

    for message in messages:
        role = message["role"]
        content = message["content"]
        if role == "system":
            normalized.append(SystemMessage(content=content))
        elif role == "assistant":
            normalized.append(AIMessage(content=content))
        else:
            normalized.append(HumanMessage(content=content))

    return normalized


def _content_to_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        parts: list[str] = []
        for item in value:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict) and isinstance(item.get("text"), str):
                parts.append(item["text"])
        return "".join(parts)
    return str(value)


def _extract_usage(response: Any) -> GatewayUsage | None:
    usage = getattr(response, "usage_metadata", None)
    if isinstance(usage, dict):
        return GatewayUsage(
            prompt_tokens=usage.get("input_tokens") or usage.get("prompt_tokens"),
            completion_tokens=usage.get("output_tokens") or usage.get("completion_tokens"),
        )

    response_metadata = getattr(response, "response_metadata", None)
    if isinstance(response_metadata, dict):
        token_usage = response_metadata.get("token_usage")
        if isinstance(token_usage, dict):
            return GatewayUsage(
                prompt_tokens=token_usage.get("prompt_tokens"),
                completion_tokens=token_usage.get("completion_tokens"),
            )

    return None


def _safe_parse_json(content: str) -> Any | None:
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", content, re.IGNORECASE)
        if not fence_match:
            return None
        try:
            return json.loads(fence_match.group(1))
        except json.JSONDecodeError:
            return None


async def complete_text(request: GatewayRequest) -> GatewayCompletionResponse:
    model_runtime = build_model_runtime(
        task_name=request.task_name,
        task_kind=_task_kind(request.task_name),
        temperature=request.temperature,
        max_tokens=request.max_tokens,
        model_override=request.model,
    )

    try:
        response = await model_runtime.client.ainvoke(
            _normalize_messages(request.messages, request.system_prompt)
        )
    except Exception as error:  # pragma: no cover
        raise ProviderExecutionError(str(error)) from error

    return GatewayCompletionResponse(
        content=_content_to_text(getattr(response, "content", "")),
        provider_id=model_runtime.provider,
        model_id=model_runtime.model,
        usage=_extract_usage(response),
    )


async def complete_json(request: GatewayRequest) -> GatewayJsonResponse:
    response = await complete_text(request)
    return GatewayJsonResponse(
        content=response.content,
        provider_id=response.provider_id,
        model_id=response.model_id,
        usage=response.usage,
        parsed=_safe_parse_json(response.content),
    )


async def stream_text(request: GatewayRequest) -> AsyncIterator[str]:
    model_runtime = build_model_runtime(
        task_name=request.task_name,
        task_kind=_task_kind(request.task_name),
        temperature=request.temperature,
        max_tokens=request.max_tokens,
        model_override=request.model,
    )

    try:
        async for chunk in model_runtime.client.astream(
            _normalize_messages(request.messages, request.system_prompt)
        ):
            if isinstance(chunk, AIMessageChunk):
                delta = _content_to_text(chunk.content)
            else:
                delta = _content_to_text(getattr(chunk, "content", ""))
            if delta:
                yield delta
    except Exception as error:  # pragma: no cover
        raise ProviderExecutionError(str(error)) from error
