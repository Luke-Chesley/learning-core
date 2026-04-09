# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Setup
uv venv --python 3.12
uv sync --extra dev

# Run the API server (http://127.0.0.1:8000)
uv run learning-core

# Run all tests
pytest

# Run a single test file
pytest tests/test_skill_registry.py

# Run with coverage
pytest --cov=learning_core
```

## Architecture

**learning-core** is a headless Python/FastAPI service that owns the AI agent runtime for learning products. It exposes typed AI operations via REST — product repos call this service and handle their own persistence/auth.

### Request Flow

```
POST /v1/operations/{operation_name}/execute
  → FastAPI validates OperationEnvelope (Pydantic)
  → AgentEngine.execute() (runtime/engine.py)
      → SkillRegistry looks up skill by operation name
      → Parses input against skill's input_model
      → Creates RuntimeContext
      → Skill.execute()
          → StructuredOutputSkill calls engine.run_structured_output()
          → Builds system prompt (from SKILL.md) + user prompt (from build_user_prompt())
          → Invokes LangChain model (Anthropic/OpenAI/Ollama)
          → Logs exchange to logs/YYYY-MM-DD/
          → Returns artifact + ExecutionLineage + ExecutionTrace
  → OperationExecuteResponse
```

### Skill Anatomy

Each operation lives in `learning_core/skills/{skill_name}/` with this structure:

```
skill_name/
├── SKILL.md          # System prompt (loaded from file at runtime)
├── scripts/
│   ├── main.py       # Skill class + build_user_prompt()
│   ├── policy.py     # ExecutionPolicy (temperature, max_tokens, task_kind)
│   ├── schemas.py    # Input & output Pydantic models
│   └── tooling.py    # Allowed tools list
└── examples/         # Test fixtures (optional)
```

All skills are registered in `learning_core/skills/catalog.py`. To add a new operation, create the skill directory and register it there.

### Key Contracts (`learning_core/contracts/`)

- **`OperationEnvelope`** — request wrapper: `{input, app_context, presentation_context, user_authored_context}`
- **`AppContext`** — product/surface metadata passed by caller
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
