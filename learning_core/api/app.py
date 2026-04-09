from __future__ import annotations

import json
import os

import uvicorn
from fastapi import FastAPI, Header
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

from learning_core.runtime.env import load_runtime_env
from learning_core.runtime.engine import AgentEngine
from learning_core.runtime.errors import LearningCoreError
from learning_core.runtime.gateway import (
    GatewayRequest,
    complete_json,
    complete_text,
    stream_text,
)
from learning_core.skills.catalog import build_skill_registry

load_runtime_env()


class OperationRequest(BaseModel):
    input: dict
    request_id: str | None = None


class GatewayRequestModel(BaseModel):
    task_name: str
    messages: list[dict[str, str]]
    system_prompt: str | None = None
    temperature: float | None = None
    max_tokens: int | None = None
    model: str | None = None


async def _authorize(api_key_header: str | None):
    configured = (os.getenv("LEARNING_CORE_API_KEY") or "").strip()
    if not configured:
        return
    if api_key_header != configured:
        raise LearningCoreError("Invalid learning-core API key.")


def create_app() -> FastAPI:
    app = FastAPI(title="learning-core", version="0.1.0")
    engine = AgentEngine(build_skill_registry())

    @app.exception_handler(LearningCoreError)
    async def handle_learning_core_error(_, exc: LearningCoreError):
        return JSONResponse(status_code=422, content={"error": str(exc)})

    @app.get("/healthz")
    async def healthz():
        return {"status": "ok"}

    @app.get("/v1/operations")
    async def list_operations():
        return {"operations": engine.skill_registry.list_operations()}

    @app.post("/v1/gateway/complete")
    async def gateway_complete(
        request: GatewayRequestModel,
        x_learning_core_key: str | None = Header(default=None),
    ):
        await _authorize(x_learning_core_key)
        response = await complete_text(GatewayRequest(**request.model_dump()))
        return response.model_dump()

    @app.post("/v1/gateway/complete-json")
    async def gateway_complete_json(
        request: GatewayRequestModel,
        x_learning_core_key: str | None = Header(default=None),
    ):
        await _authorize(x_learning_core_key)
        response = await complete_json(GatewayRequest(**request.model_dump()))
        return response.model_dump()

    @app.post("/v1/gateway/stream")
    async def gateway_stream(
        request: GatewayRequestModel,
        x_learning_core_key: str | None = Header(default=None),
    ):
        await _authorize(x_learning_core_key)
        gateway_request = GatewayRequest(**request.model_dump())

        async def event_stream():
            try:
                async for delta in stream_text(gateway_request):
                    yield json.dumps({"delta": delta, "done": False}) + "\n"
                yield json.dumps({"delta": "", "done": True}) + "\n"
            except LearningCoreError as error:
                yield json.dumps({"error": str(error), "done": True}) + "\n"

        return StreamingResponse(event_stream(), media_type="application/x-ndjson")

    @app.post("/v1/operations/generate-activities-from-plan-session/prompt-preview")
    async def activity_prompt_preview(
        request: OperationRequest,
        x_learning_core_key: str | None = Header(default=None),
    ):
        await _authorize(x_learning_core_key)
        preview = engine.preview("generate-activities-from-plan-session", request.input)
        return preview.model_dump()

    @app.post("/v1/operations/generate-activities-from-plan-session/execute")
    async def activity_execute(
        request: OperationRequest,
        x_learning_core_key: str | None = Header(default=None),
    ):
        await _authorize(x_learning_core_key)
        result = engine.execute(
            "generate-activities-from-plan-session",
            request.input,
            request_id=request.request_id,
        )
        return {
            "artifact": result.artifact.model_dump(),
            "lineage": result.lineage.model_dump(),
            "trace": result.trace.model_dump(),
        }

    return app


app = create_app()


def main() -> None:
    uvicorn.run(
        "learning_core.api.app:app",
        host=os.getenv("LEARNING_CORE_HOST", "127.0.0.1"),
        port=int(os.getenv("LEARNING_CORE_PORT", "8000")),
        reload=False,
    )
