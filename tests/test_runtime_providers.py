from learning_core.runtime.providers import build_model_runtime


def test_openai_service_tier_from_env(monkeypatch):
    monkeypatch.setenv("LEARNING_CORE_PROVIDER", "openai")
    monkeypatch.setenv("LEARNING_CORE_DEFAULT_TEMPERATURE", "0.2")
    monkeypatch.setenv("LEARNING_CORE_MAX_TOKENS", "4096")
    monkeypatch.setenv("LEARNING_CORE_CHAT_MODEL", "gpt-5.4-mini")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_SERVICE_TIER", "flex")
    monkeypatch.delenv("LEARNING_CORE_CHAT_MAX_TOKENS", raising=False)
    monkeypatch.delenv("LEARNING_CORE_COPILOT_CHAT_MAX_TOKENS", raising=False)
    monkeypatch.delenv("LEARNING_CORE_ACTIVITY_GENERATE_MAX_TOKENS", raising=False)

    runtime = build_model_runtime(
        task_name="copilot_chat",
        task_kind="chat",
        temperature=None,
        max_tokens=None,
    )

    assert runtime.provider == "openai"
    assert runtime.client.service_tier == "flex"
    assert runtime.provider_settings["openai_service_tier"] == "flex"
    assert runtime.max_tokens == 4096
    assert runtime.max_tokens_source == "LEARNING_CORE_MAX_TOKENS"


def test_openai_service_tier_omits_flex_for_curriculum_generate(monkeypatch):
    monkeypatch.setenv("LEARNING_CORE_PROVIDER", "openai")
    monkeypatch.setenv("LEARNING_CORE_DEFAULT_TEMPERATURE", "0.2")
    monkeypatch.setenv("LEARNING_CORE_MAX_TOKENS", "4096")
    monkeypatch.setenv("LEARNING_CORE_GENERATION_MODEL", "gpt-5.4-mini")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_SERVICE_TIER", "flex")

    runtime = build_model_runtime(
        task_name="curriculum_generate",
        task_kind="generation",
        temperature=None,
        max_tokens=None,
    )

    assert runtime.client.service_tier is None
    assert runtime.provider_settings["openai_service_tier"] is None


def test_openai_service_tier_omits_flex_for_source_interpret(monkeypatch):
    monkeypatch.setenv("LEARNING_CORE_PROVIDER", "openai")
    monkeypatch.setenv("LEARNING_CORE_DEFAULT_TEMPERATURE", "0.2")
    monkeypatch.setenv("LEARNING_CORE_MAX_TOKENS", "4096")
    monkeypatch.setenv("LEARNING_CORE_GENERATION_MODEL", "gpt-5.4-mini")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_SERVICE_TIER", "flex")

    runtime = build_model_runtime(
        task_name="source_interpret",
        task_kind="generation",
        temperature=None,
        max_tokens=None,
    )

    assert runtime.client.service_tier is None
    assert runtime.provider_settings["openai_service_tier"] is None


def test_openai_service_tier_omitted_when_blank(monkeypatch):
    monkeypatch.setenv("LEARNING_CORE_PROVIDER", "openai")
    monkeypatch.setenv("LEARNING_CORE_DEFAULT_TEMPERATURE", "0.2")
    monkeypatch.setenv("LEARNING_CORE_MAX_TOKENS", "4096")
    monkeypatch.setenv("LEARNING_CORE_CHAT_MODEL", "gpt-5.4-mini")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_SERVICE_TIER", "   ")
    monkeypatch.delenv("LEARNING_CORE_CHAT_MAX_TOKENS", raising=False)
    monkeypatch.delenv("LEARNING_CORE_ACTIVITY_GENERATE_MAX_TOKENS", raising=False)

    runtime = build_model_runtime(
        task_name="activity_generate",
        task_kind="chat",
        temperature=None,
        max_tokens=None,
    )

    assert runtime.client.service_tier is None
    assert runtime.provider_settings["openai_service_tier"] is None
    assert runtime.max_tokens == 4096
    assert runtime.max_tokens_source == "LEARNING_CORE_MAX_TOKENS"


def test_openai_service_tier_keeps_flex_for_chat_tasks(monkeypatch):
    monkeypatch.setenv("LEARNING_CORE_PROVIDER", "openai")
    monkeypatch.setenv("LEARNING_CORE_DEFAULT_TEMPERATURE", "0.2")
    monkeypatch.setenv("LEARNING_CORE_MAX_TOKENS", "4096")
    monkeypatch.setenv("LEARNING_CORE_CHAT_MODEL", "gpt-5.4-mini")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_SERVICE_TIER", "flex")

    runtime = build_model_runtime(
        task_name="copilot_chat",
        task_kind="chat",
        temperature=None,
        max_tokens=None,
    )

    assert runtime.client.service_tier == "flex"
    assert runtime.provider_settings["openai_service_tier"] == "flex"


def test_max_tokens_env_precedence_overrides_skill_policy(monkeypatch):
    monkeypatch.setenv("LEARNING_CORE_PROVIDER", "openai")
    monkeypatch.setenv("LEARNING_CORE_DEFAULT_TEMPERATURE", "0.2")
    monkeypatch.setenv("LEARNING_CORE_MAX_TOKENS", "2048")
    monkeypatch.setenv("LEARNING_CORE_CHAT_MAX_TOKENS", "3072")
    monkeypatch.setenv("LEARNING_CORE_COPILOT_CHAT_MAX_TOKENS", "5120")
    monkeypatch.setenv("LEARNING_CORE_CHAT_MODEL", "gpt-5.4-mini")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    runtime = build_model_runtime(
        task_name="copilot_chat",
        task_kind="chat",
        temperature=None,
        max_tokens=4096,
    )

    assert runtime.max_tokens == 5120
    assert runtime.max_tokens_source == "LEARNING_CORE_COPILOT_CHAT_MAX_TOKENS"


def test_openai_runtime_reuses_matching_client_instances(monkeypatch):
    monkeypatch.setenv("LEARNING_CORE_PROVIDER", "openai")
    monkeypatch.setenv("LEARNING_CORE_DEFAULT_TEMPERATURE", "0.2")
    monkeypatch.setenv("LEARNING_CORE_MAX_TOKENS", "4096")
    monkeypatch.setenv("LEARNING_CORE_CHAT_MODEL", "gpt-5.4-mini")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.delenv("OPENAI_SERVICE_TIER", raising=False)

    first = build_model_runtime(
        task_name="copilot_chat",
        task_kind="chat",
        temperature=None,
        max_tokens=None,
    )
    second = build_model_runtime(
        task_name="copilot_chat",
        task_kind="chat",
        temperature=None,
        max_tokens=None,
    )

    assert first.client is second.client
