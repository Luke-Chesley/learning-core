from fastapi.testclient import TestClient

from learning_core.api.app import create_app
from learning_core.runtime.errors import ConfigurationError


def test_gateway_stream_returns_error_event_for_learning_core_errors(monkeypatch):
    async def fake_stream_text(_request):
        raise ConfigurationError("LEARNING_CORE_PROVIDER is required.")
        yield ""

    monkeypatch.setattr("learning_core.api.app.stream_text", fake_stream_text)

    client = TestClient(create_app())
    response = client.post(
        "/v1/gateway/stream",
        json={
            "task_name": "chat.answer",
            "messages": [{"role": "user", "content": "test"}],
        },
    )

    assert response.status_code == 200
    assert '{"error": "LEARNING_CORE_PROVIDER is required.", "done": true}' in response.text
