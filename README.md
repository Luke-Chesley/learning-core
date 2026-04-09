# learning-core

`learning-core` is the headless Python service that owns AI runtime concerns for learning products.

## Scope

- Owns: agent runtime, skill registry, prompt/`SKILL.md` loading, contracts, workflow semantics, validation, and observability.
- Does not own: product UI, product DB tables, auth, or persistence policy for app records.

## Current Slice

- Fully scaffolded runtime for the long-term split.
- First implemented operation: `generate-activities-from-plan-session`.
- Remaining seven operations are registered as explicit fail-fast stubs.

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
   - `LEARNING_CORE_CHAT_MODEL`
   - `LEARNING_CORE_FAST_MODEL`
   - `LEARNING_CORE_GENERATION_MODEL`
   - provider credential/base-url vars for the selected backend
6. Run the API:
   - `uv run learning-core`

The service defaults to `http://127.0.0.1:8000`.

## Folder Tree

```text
learning_core/
  api/
  contracts/
  observability/
  runtime/
  skills/
    activity_generate/
    curriculum_generate/
    curriculum_revise/
    progression_generate/
    progression_revise/
    session_generate/
    session_evaluate/
    curriculum_update_propose/
```

## API

- `GET /healthz`
- `GET /v1/operations`
- `POST /v1/gateway/complete`
- `POST /v1/gateway/complete-json`
- `POST /v1/gateway/stream`
- `POST /v1/operations/generate-activities-from-plan-session/prompt-preview`
- `POST /v1/operations/generate-activities-from-plan-session/execute`

## Design Rules

- No silent fallbacks.
- Unknown operation names fail immediately.
- Missing model/provider config fails immediately.
- Runtime/provider defaults do not live in code; define them in `.env.local`.
- Contract mismatches fail immediately.
- Product repos persist artifacts; `learning-core` returns typed artifacts.
