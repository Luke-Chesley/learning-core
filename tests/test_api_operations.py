from fastapi.testclient import TestClient

from learning_core.api.app import create_app


def test_list_operations_returns_metadata():
    client = TestClient(create_app())

    response = client.get("/v1/operations")

    assert response.status_code == 200
    payload = response.json()
    assert "operations" in payload
    assert any(operation["operation_name"] == "activity_generate" for operation in payload["operations"])


def test_list_operations_includes_required_cutover_operations():
    client = TestClient(create_app())

    response = client.get("/v1/operations")

    assert response.status_code == 200
    operation_names = {operation["operation_name"] for operation in response.json()["operations"]}
    assert {
        "activity_generate",
        "session_generate",
        "curriculum_generate",
        "curriculum_revise",
        "progression_generate",
        "progression_revise",
        "session_evaluate",
        "curriculum_update_propose",
        "curriculum_intake",
        "copilot_chat",
    }.issubset(operation_names)


def test_legacy_gateway_endpoints_are_gone():
    client = TestClient(create_app())

    assert client.post("/v1/gateway/complete").status_code == 404
    assert client.post("/v1/gateway/complete-json").status_code == 404
    assert client.post("/v1/gateway/stream").status_code == 404
