from learning_core.runtime.providers import build_model_runtime


def test_openai_service_tier_from_env(monkeypatch):
    monkeypatch.setenv("LEARNING_CORE_PROVIDER", "openai")
    monkeypatch.setenv("LEARNING_CORE_DEFAULT_TEMPERATURE", "0.2")
    monkeypatch.setenv("LEARNING_CORE_MAX_TOKENS", "4096")
    monkeypatch.setenv("LEARNING_CORE_CHAT_MODEL", "gpt-5.4-mini")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_SERVICE_TIER", "flex")

    runtime = build_model_runtime(
        task_name="generate-activities-from-plan-session",
        task_kind="chat",
        temperature=None,
        max_tokens=None,
    )

    assert runtime.provider == "openai"
    assert runtime.client.service_tier == "flex"


def test_openai_service_tier_omitted_when_blank(monkeypatch):
    monkeypatch.setenv("LEARNING_CORE_PROVIDER", "openai")
    monkeypatch.setenv("LEARNING_CORE_DEFAULT_TEMPERATURE", "0.2")
    monkeypatch.setenv("LEARNING_CORE_MAX_TOKENS", "4096")
    monkeypatch.setenv("LEARNING_CORE_CHAT_MODEL", "gpt-5.4-mini")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_SERVICE_TIER", "   ")

    runtime = build_model_runtime(
        task_name="generate-activities-from-plan-session",
        task_kind="chat",
        temperature=None,
        max_tokens=None,
    )

    assert runtime.client.service_tier is None
