# learning-core

`learning-core` is the headless Python service that owns AI runtime concerns for learning products.

## Scope

- Owns: agent runtime, skill registry, prompt/`SKILL.md` loading, contracts, workflow semantics, validation, and observability.
- Does not own: product UI, product DB tables, auth, or persistence policy for app records.

## Current Slice

- Shared operation-envelope runtime is in place.
- All extracted operations are exposed through `/v1/operations/{operation_name}`.
- Prompt ownership lives in `SKILL.md` plus Python prompt builders inside `learning-core`.
- Skill runtime code lives under `learning_core/skills/<skill>/scripts/main.py` and any
  skill-local helper modules live alongside it in `scripts/`.

## Local Dev

1. Use `uv` with Python `3.12`.
   - `.python-version` is pinned to `3.12`.
   - `requires-python` is `>=3.12,<3.13`.
2. Install Python `3.12` if it is not already available:
   - `uv python install 3.12`
3. Create the virtualenv with `uv`:
   - `uv venv --python 3.12`
4. Install dependencies with `uv`:
   - `uv sync --extra dev`
5. Copy `.env.example` to `.env.local` and fill in exactly one provider profile.
   - `LEARNING_CORE_PROVIDER`
   - `LEARNING_CORE_DEFAULT_TEMPERATURE`
   - `LEARNING_CORE_MAX_TOKENS`
   - optional token overrides:
     - `LEARNING_CORE_CHAT_MAX_TOKENS`
     - `LEARNING_CORE_FAST_MAX_TOKENS`
     - `LEARNING_CORE_GENERATION_MAX_TOKENS`
     - `LEARNING_CORE_<OPERATION_NAME>_MAX_TOKENS`
   - `LEARNING_CORE_CHAT_MODEL`
   - `LEARNING_CORE_FAST_MODEL`
   - `LEARNING_CORE_GENERATION_MODEL`
   - provider credential/base-url vars for the selected backend
6. Run the API:
   - `uv run learning-core`

The service defaults to `http://127.0.0.1:8000`.
`learning-core` now auto-loads `.env` and `.env.local` from the repo root without requiring you to `source` them first.

## Provider Logs

- Every provider request/response exchange is written to `logs/YYYY-MM-DD/`.
- Each file is named with the request timestamp.
- The top half of the file is the provider request payload.
- The bottom half is the provider response payload or provider error.
- The request block includes request classification fields such as `operation_name`, `task_kind`, `response_mode`, `provider_request_kind`, and provider-specific settings such as `openai_service_tier`.
- The request block also includes the resolved `max_tokens` and `max_tokens_source`.
- For tests or custom local setups, you can override the log root with `LEARNING_CORE_LOG_DIR`.

## Folder Tree

```text
learning_core/
  api/
  contracts/
  observability/
  runtime/
  skills/
    activity_generate/
      SKILL.md
      scripts/
        main.py
        policy.py
        schemas.py
        tooling.py
    copilot_chat/
      SKILL.md
      scripts/
        main.py
    curriculum_generate/
      SKILL.md
      scripts/
        main.py
    curriculum_intake/
      SKILL.md
      scripts/
        main.py
    curriculum_revise/
      SKILL.md
      scripts/
        main.py
    progression_generate/
      SKILL.md
      scripts/
        main.py
    progression_revise/
      SKILL.md
      scripts/
        main.py
    session_generate/
      SKILL.md
      scripts/
        main.py
    session_evaluate/
      SKILL.md
      scripts/
        main.py
    curriculum_update_propose/
      SKILL.md
      scripts/
        main.py
```

## API

- `GET /healthz`
- `GET /v1/operations`
- `POST /v1/operations/{operation_name}/prompt-preview`
- `POST /v1/operations/{operation_name}/execute`

Current first-class operations:

- `activity_generate`
- `session_generate`
- `curriculum_intake`
- `copilot_chat`
- `curriculum_generate`
- `curriculum_revise`
- `progression_generate`
- `progression_revise`
- `session_evaluate`
- `curriculum_update_propose`

## Design Rules

- No silent fallbacks.
- Unknown operation names fail immediately.
- Missing model/provider config fails immediately.
- Runtime/provider defaults do not live in code; define them in `.env.local`.
- Contract mismatches fail immediately.
- Product repos persist artifacts; `learning-core` returns typed artifacts, lineage, and traces.
- Product repos send structured request envelopes only. They do not send prompt fragments or raw system prompts.
- The legacy generic gateway surface is deleted. Apps call named operations only.
