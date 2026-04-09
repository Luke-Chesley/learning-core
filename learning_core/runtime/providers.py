from __future__ import annotations

import os
from dataclasses import dataclass

from langchain_anthropic import ChatAnthropic
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI

from learning_core.runtime.env import load_runtime_env
from learning_core.runtime.errors import ConfigurationError

load_runtime_env()


@dataclass(frozen=True)
class ModelRuntime:
    provider: str
    model: str
    client: object


def _parse_optional_int(value: str | None) -> int | None:
    if value is None:
        return None
    stripped = value.strip()
    if not stripped:
        return None
    parsed = int(stripped)
    return parsed if parsed > 0 else None


def _parse_optional_str(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _read_required_str(name: str) -> str:
    value = _parse_optional_str(os.getenv(name))
    if value is None:
        raise ConfigurationError(f"{name} is required.")
    return value


def _read_required_int(name: str) -> int:
    value = _parse_optional_int(os.getenv(name))
    if value is None:
        raise ConfigurationError(f"{name} is required and must be a positive integer.")
    return value


def _read_required_float(name: str) -> float:
    raw_value = os.getenv(name)
    if raw_value is None or not raw_value.strip():
        raise ConfigurationError(f"{name} is required and must be a float.")
    try:
        return float(raw_value.strip())
    except ValueError as error:
        raise ConfigurationError(f"{name} must be a float.") from error


def _read_provider() -> str:
    provider = (os.getenv("LEARNING_CORE_PROVIDER") or "").strip().lower()
    if not provider:
        raise ConfigurationError("LEARNING_CORE_PROVIDER is required.")
    if provider not in {"anthropic", "openai", "ollama"}:
        raise ConfigurationError(f"Unsupported LEARNING_CORE_PROVIDER '{provider}'.")
    return provider


def _resolve_model(task_name: str, task_kind: str, model_override: str | None) -> str:
    if model_override and not model_override.startswith("learning-core/"):
        return model_override

    env_var_name = {
        "chat": _parse_optional_str(os.getenv("LEARNING_CORE_CHAT_MODEL")),
        "fast": _parse_optional_str(os.getenv("LEARNING_CORE_FAST_MODEL")),
        "generation": _parse_optional_str(os.getenv("LEARNING_CORE_GENERATION_MODEL")),
    }.get(task_kind)

    if env_var_name:
        return env_var_name

    fallback = _parse_optional_str(os.getenv("LEARNING_CORE_FALLBACK_MODEL"))
    if fallback:
        return fallback

    raise ConfigurationError(
        "Model routing is incomplete for "
        f"task '{task_name}'. Set LEARNING_CORE_{task_kind.upper()}_MODEL "
        "or LEARNING_CORE_FALLBACK_MODEL."
    )


def build_model_runtime(
    *,
    task_name: str,
    task_kind: str,
    temperature: float | None,
    max_tokens: int | None,
    model_override: str | None = None,
) -> ModelRuntime:
    provider = _read_provider()
    model = _resolve_model(task_name, task_kind, model_override)
    resolved_temperature = (
        _read_required_float("LEARNING_CORE_DEFAULT_TEMPERATURE")
        if temperature is None
        else temperature
    )
    resolved_max_tokens = (
        _read_required_int("LEARNING_CORE_MAX_TOKENS")
        if max_tokens is None
        else max_tokens
    )

    if provider == "anthropic":
        api_key = _read_required_str("ANTHROPIC_API_KEY")
        client = ChatAnthropic(
            model=model,
            temperature=resolved_temperature,
            max_tokens=resolved_max_tokens,
            anthropic_api_key=api_key,
            timeout=None,
        )
        return ModelRuntime(provider=provider, model=model, client=client)

    if provider == "openai":
        api_key = _read_required_str("OPENAI_API_KEY")
        service_tier = _parse_optional_str(os.getenv("OPENAI_SERVICE_TIER"))
        client = ChatOpenAI(
            model=model,
            temperature=resolved_temperature,
            max_tokens=resolved_max_tokens,
            api_key=api_key,
            service_tier=service_tier,
            timeout=None,
        )
        return ModelRuntime(provider=provider, model=model, client=client)

    base_url = _read_required_str("OLLAMA_BASE_URL")
    auth_token = _parse_optional_str(os.getenv("OLLAMA_AUTH_TOKEN"))
    num_ctx = _parse_optional_int(os.getenv("OLLAMA_NUM_CTX"))
    keep_alive = _parse_optional_str(os.getenv("OLLAMA_KEEP_ALIVE"))
    client_kwargs = {"headers": {"Authorization": f"Bearer {auth_token}"}} if auth_token else None
    client = ChatOllama(
        model=model,
        base_url=base_url,
        temperature=resolved_temperature,
        num_predict=resolved_max_tokens,
        num_ctx=num_ctx,
        keep_alive=keep_alive,
        client_kwargs=client_kwargs,
    )
    return ModelRuntime(provider=provider, model=model, client=client)
