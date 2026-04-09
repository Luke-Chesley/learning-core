import os

from learning_core.runtime.env import load_runtime_env


def test_env_local_overrides_dot_env_for_unset_process_values(monkeypatch, tmp_path):
    (tmp_path / ".env").write_text(
        "LEARNING_CORE_PROVIDER=anthropic\nLEARNING_CORE_FALLBACK_MODEL=from-dot-env\n",
        encoding="utf-8",
    )
    (tmp_path / ".env.local").write_text(
        "LEARNING_CORE_PROVIDER=openai\nLEARNING_CORE_FALLBACK_MODEL=from-dot-local\n",
        encoding="utf-8",
    )

    monkeypatch.delenv("LEARNING_CORE_PROVIDER", raising=False)
    monkeypatch.delenv("LEARNING_CORE_FALLBACK_MODEL", raising=False)

    load_runtime_env(search_roots=[tmp_path], force=True)

    assert os.environ["LEARNING_CORE_PROVIDER"] == "openai"
    assert os.environ["LEARNING_CORE_FALLBACK_MODEL"] == "from-dot-local"


def test_runtime_env_does_not_override_existing_process_values(monkeypatch, tmp_path):
    (tmp_path / ".env.local").write_text(
        "LEARNING_CORE_PROVIDER=openai\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("LEARNING_CORE_PROVIDER", "ollama")

    load_runtime_env(search_roots=[tmp_path], force=True)

    assert os.environ["LEARNING_CORE_PROVIDER"] == "ollama"
