from __future__ import annotations

import os

import uvicorn
from fastapi import FastAPI, Header
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse

from learning_core.contracts.operation import OperationEnvelope
from learning_core.runtime.env import load_runtime_env
from learning_core.runtime.engine import AgentEngine
from learning_core.runtime.errors import LearningCoreError
from learning_core.skills.catalog import build_skill_registry

load_runtime_env()


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
        return {"operations": [operation.model_dump() for operation in engine.skill_registry.list_operations()]}

    @app.get("/v1/runtime/status")
    async def runtime_status(x_learning_core_key: str | None = Header(default=None)):
        await _authorize(x_learning_core_key)
        return {
            "status": "ok",
            "service": "learning-core",
            "version": "0.1.0",
            "authRequired": bool((os.getenv("LEARNING_CORE_API_KEY") or "").strip()),
            "operations": [operation.operation_name for operation in engine.skill_registry.list_operations()],
        }

    @app.post("/v1/operations/{operation_name}/prompt-preview")
    async def operation_prompt_preview(
        operation_name: str,
        request: OperationEnvelope,
        x_learning_core_key: str | None = Header(default=None),
    ):
        await _authorize(x_learning_core_key)
        preview = await run_in_threadpool(engine.preview, operation_name, request.model_dump(mode="json"))
        return preview.model_dump()

    @app.post("/v1/operations/{operation_name}/execute")
    async def operation_execute(
        operation_name: str,
        request: OperationEnvelope,
        x_learning_core_key: str | None = Header(default=None),
    ):
        await _authorize(x_learning_core_key)
        result = await run_in_threadpool(engine.execute, operation_name, request.model_dump(mode="json"))
        return result.model_dump()

    return app


app = create_app()


def main() -> None:
    uvicorn.run(
        "learning_core.api.app:app",
        host=os.getenv("LEARNING_CORE_HOST", "127.0.0.1"),
        port=int(os.getenv("LEARNING_CORE_PORT", "8000")),
        reload=False,
    )
