import asyncio

from learning_core.api.app import create_app


def _route_for_path(app, path: str):
    return next(route for route in app.router.routes if getattr(route, "path", None) == path)


def test_list_operations_returns_metadata():
    app = create_app()
    route = _route_for_path(app, "/v1/operations")

    payload = asyncio.run(route.endpoint())

    assert "operations" in payload
    assert any(operation["operation_name"] == "activity_generate" for operation in payload["operations"])
    assert any(operation["operation_name"] == "activity_feedback" for operation in payload["operations"])
    assert any(operation["operation_name"] == "widget_transition" for operation in payload["operations"])


def test_list_operations_includes_required_cutover_operations():
    app = create_app()
    route = _route_for_path(app, "/v1/operations")

    payload = asyncio.run(route.endpoint())

    operation_names = {operation["operation_name"] for operation in payload["operations"]}
    assert {
        "activity_generate",
        "activity_feedback",
        "widget_transition",
        "session_generate",
        "curriculum_generate",
        "curriculum_revise",
        "launch_plan_generate",
        "progression_generate",
        "progression_revise",
        "session_evaluate",
        "curriculum_update_propose",
        "curriculum_intake",
        "copilot_chat",
    }.issubset(operation_names)


def test_legacy_gateway_endpoints_are_gone():
    app = create_app()
    paths = {getattr(route, "path", None) for route in app.router.routes}

    assert "/v1/gateway/complete" not in paths
    assert "/v1/gateway/complete-json" not in paths
    assert "/v1/gateway/stream" not in paths
