from __future__ import annotations

from pathlib import Path

from learning_core.observability.provider_logs import write_provider_exchange_log


def test_write_provider_exchange_log_creates_daily_log_file(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("LEARNING_CORE_LOG_DIR", str(tmp_path / "logs"))

    path = write_provider_exchange_log(
        request={
            "operation_name": "copilot_chat",
            "max_tokens": 4096,
            "max_tokens_source": "LEARNING_CORE_CHAT_MAX_TOKENS",
            "provider_messages": [
                {"role": "system", "content": "System prompt"},
                {"role": "user", "content": "Hello"},
            ],
        },
        response={
            "status": "success",
            "normalized_text": "Hi there.",
        },
    )

    assert path.exists()
    assert path.parent.parent == tmp_path / "logs"
    body = path.read_text(encoding="utf-8")
    assert "REQUEST" in body
    assert "RESPONSE" in body
    assert '"operation_name": "copilot_chat"' in body
    assert '"max_tokens": 4096' in body
    assert '"max_tokens_source": "LEARNING_CORE_CHAT_MAX_TOKENS"' in body
    assert '"normalized_text": "Hi there."' in body
