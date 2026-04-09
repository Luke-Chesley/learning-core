# learning-core

`learning-core` is the headless Python service that owns AI runtime concerns for learning products.

## Scope

- Owns: agent runtime, skill registry, prompt/`SKILL.md` loading, contracts, workflow semantics, validation, and observability.
- Does not own: product UI, product DB tables, auth, or persistence policy for app records.

## Current Slice

- Shared operation-envelope runtime is in place.
- All extracted operations are exposed through `/v1/operations/{operation_name}`.
- Prompt ownership lives in `SKILL.md` plus Python prompt builders inside `learning-core`.

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
`learning-core` now auto-loads `.env` and `.env.local` from the repo root without requiring you to `source` them first.

## Folder Tree

```text
learning_core/
  api/
  contracts/
  observability/
  runtime/
  skills/
    activity_generate/
    copilot_chat/
    curriculum_generate/
    curriculum_intake/
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
