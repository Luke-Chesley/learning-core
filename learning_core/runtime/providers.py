from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache

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
    temperature: float
    max_tokens: int
    max_tokens_source: str
    provider_settings: dict[str, object]


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


_OPENAI_FLEX_UNSTABLE_TASKS = {
    "activity_generate",
    "bounded_plan_generate",
    "source_interpret",
    "session_generate",
}


def _read_required_str(name: str) -> str:
    value = _parse_optional_str(os.getenv(name))
    if value is None:
        raise ConfigurationError(f"{name} is required.")
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


def _resolve_max_tokens(task_name: str, task_kind: str, policy_max_tokens: int | None) -> tuple[int, str]:
    operation_env_name = f"LEARNING_CORE_{task_name.upper()}_MAX_TOKENS"
    operation_override = _parse_optional_int(os.getenv(operation_env_name))
    if operation_override is not None:
        return operation_override, operation_env_name

    task_kind_env_name = f"LEARNING_CORE_{task_kind.upper()}_MAX_TOKENS"
    task_kind_override = _parse_optional_int(os.getenv(task_kind_env_name))
    if task_kind_override is not None:
        return task_kind_override, task_kind_env_name

    global_override = _parse_optional_int(os.getenv("LEARNING_CORE_MAX_TOKENS"))
    if global_override is not None:
        return global_override, "LEARNING_CORE_MAX_TOKENS"

    if policy_max_tokens is not None:
        return policy_max_tokens, "skill_policy"

    raise ConfigurationError(
        "Max token routing is incomplete for "
        f"task '{task_name}'. Set {operation_env_name}, {task_kind_env_name}, "
        "LEARNING_CORE_MAX_TOKENS, or a skill policy override."
    )


def _resolve_openai_service_tier(task_name: str) -> str | None:
    service_tier = _parse_optional_str(os.getenv("OPENAI_SERVICE_TIER"))
    if service_tier != "flex":
        return service_tier

    # Flex is fast for lighter requests, but the larger structured and agentic
    # generation calls on the onboarding path have been materially less stable
    # there than on the default tier.
    if task_name in _OPENAI_FLEX_UNSTABLE_TASKS:
        return None

    return service_tier


@lru_cache(maxsize=32)
def _build_anthropic_client(
    model: str,
    temperature: float,
    max_tokens: int,
    api_key: str,
):
    return ChatAnthropic(
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        anthropic_api_key=api_key,
        timeout=None,
    )


@lru_cache(maxsize=32)
def _build_openai_client(
    model: str,
    temperature: float,
    max_tokens: int,
    api_key: str,
    service_tier: str | None,
):
    return ChatOpenAI(
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        api_key=api_key,
        service_tier=service_tier,
        timeout=None,
        use_responses_api=True,
    )


@lru_cache(maxsize=32)
def _build_ollama_client(
    model: str,
    base_url: str,
    temperature: float,
    max_tokens: int,
    num_ctx: int | None,
    keep_alive: str | None,
    auth_token: str | None,
):
    client_kwargs = {"headers": {"Authorization": f"Bearer {auth_token}"}} if auth_token else None
    return ChatOllama(
        model=model,
        base_url=base_url,
        temperature=temperature,
        num_predict=max_tokens,
        num_ctx=num_ctx,
        keep_alive=keep_alive,
        client_kwargs=client_kwargs,
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
    resolved_max_tokens, max_tokens_source = _resolve_max_tokens(task_name, task_kind, max_tokens)

    if provider == "anthropic":
        api_key = _read_required_str("ANTHROPIC_API_KEY")
        client = _build_anthropic_client(
            model,
            resolved_temperature,
            resolved_max_tokens,
            api_key,
        )
        return ModelRuntime(
            provider=provider,
            model=model,
            client=client,
            temperature=resolved_temperature,
            max_tokens=resolved_max_tokens,
            max_tokens_source=max_tokens_source,
            provider_settings={},
        )

    if provider == "openai":
        api_key = _read_required_str("OPENAI_API_KEY")
        service_tier = _resolve_openai_service_tier(task_name)
        client = _build_openai_client(
            model,
            resolved_temperature,
            resolved_max_tokens,
            api_key,
            service_tier,
        )
        return ModelRuntime(
            provider=provider,
            model=model,
            client=client,
            temperature=resolved_temperature,
            max_tokens=resolved_max_tokens,
            max_tokens_source=max_tokens_source,
            provider_settings={
                "openai_service_tier": service_tier,
            },
        )

    base_url = _read_required_str("OLLAMA_BASE_URL")
    auth_token = _parse_optional_str(os.getenv("OLLAMA_AUTH_TOKEN"))
    num_ctx = _parse_optional_int(os.getenv("OLLAMA_NUM_CTX"))
    keep_alive = _parse_optional_str(os.getenv("OLLAMA_KEEP_ALIVE"))
    client = _build_ollama_client(
        model,
        base_url,
        resolved_temperature,
        resolved_max_tokens,
        num_ctx,
        keep_alive,
        auth_token,
    )
    return ModelRuntime(
        provider=provider,
        model=model,
        client=client,
        temperature=resolved_temperature,
        max_tokens=resolved_max_tokens,
        max_tokens_source=max_tokens_source,
        provider_settings={
            "ollama_base_url": base_url,
            "ollama_num_ctx": num_ctx,
            "ollama_keep_alive": keep_alive,
        },
    )
