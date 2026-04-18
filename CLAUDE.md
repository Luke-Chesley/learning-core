# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Setup
uv venv --python 3.12
uv sync --extra dev

# Run the API server (http://127.0.0.1:8000)
uv run learning-core

# Run the local widget/debug harness
./local_test/run.sh

# Run all tests
uv run pytest

# Run a single test file
uv run pytest tests/test_skill_registry.py
```

## Architecture

**learning-core** is a FastAPI service that owns AI runtime behavior for learning products. Product repos call named operations over REST and handle their own UI, auth, and persistence.

### Request Flow

```
POST /v1/operations/{operation_name}/execute
  → FastAPI validates OperationEnvelope in learning_core/api/app.py
  → AgentEngine.execute() in runtime/engine.py
      → SkillRegistry resolves the operation's skill
      → normalize_runtime_request() maps the envelope onto the shared runtime model
      → AgentKernel.preview()/execute() resolves:
          → task_profile
          → response_type
          → workflow_card
          → runtime packs
          → tool plan
      → execution strategy from runtime/task_profiles.py runs one of:
          → skill_execute
          → structured
          → text
      → artifact is validated, traced, and returned
  → OperationExecuteResponse
```

Internal orchestration helpers such as `AgentEngine.execute_generate_from_source()` live in `runtime/engine.py`; they are not task-profile execution strategies inside `AgentKernel`.

### Skill Anatomy

Each operation lives in `learning_core/skills/{skill_name}/`.

Common layout:

```
skill_name/
├── SKILL.md          # Prompt instructions loaded at runtime
├── scripts/
│   └── main.py       # Skill entrypoint
├── examples/         # Optional fixtures
├── packs/            # Optional skill-local pack docs/helpers
├── validation/       # Optional validators
├── ui_components/    # Optional activity component docs
└── ui_widgets/       # Optional engine-backed widget docs
```

Many skills also keep optional `policy.py`, `schemas.py`, and `tooling.py` helpers next to `main.py`.

To add a new operation:

- create or extend the skill under `learning_core/skills/`
- register it in `learning_core/skills/catalog.py`
- add runtime metadata in `learning_core/runtime/task_profiles.py`
- add or reuse the matching response type and workflow card when needed

### Key Contracts (`learning_core/contracts/`)

- **`OperationEnvelope`** — request wrapper: `{input, app_context, presentation_context, user_authored_context, request_id}`
- **`AppContext`** — product/surface metadata passed by caller
- **`PresentationContext` / `UserAuthoredContext`** — response shaping and user-provided guidance
- **`StrictModel`** (from `base.py`) — all contracts inherit this; forbids extra fields

### Provider Abstraction (`runtime/providers.py`)

Provider and model are configured via env vars. `build_model_runtime()` returns a configured LangChain client. Supported: `anthropic`, `openai`, `ollama`.

### Observability

- Every provider request/response is logged to `logs/YYYY-MM-DD/` via `write_provider_exchange_log()`
- `ExecutionTrace` captures prompts + allowed_tools; returned in response when `should_return_prompt_preview=true`

## Configuration

Copy `.env.example` to `.env.local`. Key vars:

```
LEARNING_CORE_PROVIDER=anthropic          # anthropic | openai | ollama
LEARNING_CORE_GENERATION_MODEL=...        # Model for generation tasks
LEARNING_CORE_FAST_MODEL=...              # Model for fast tasks
LEARNING_CORE_CHAT_MODEL=...              # Model for chat tasks
LEARNING_CORE_MAX_TOKENS=4096
LEARNING_CORE_<OPERATION>_MAX_TOKENS=...  # Per-operation override
```

## Design Constraints

- **No silent fallbacks** — unknown operations and contract mismatches fail immediately
- **learning-core returns artifacts; products persist them** — no product DB access here
- **Products send `OperationEnvelope`** — not raw prompts; structured requests only
