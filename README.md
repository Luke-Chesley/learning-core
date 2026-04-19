# learning-core

`learning-core` is the headless Python service that owns AI runtime concerns for learning products.

Current interactive activity generation stays bounded by the `ActivityArtifact` contract. Rich engine-backed interaction now flows through the top-level `interactive_widget` component, with backend domain engines owning canonical state and runtime evaluation.

## Scope

- Owns: agent runtime, skill registry, prompt/`SKILL.md` loading, contracts, workflow semantics, validation, and observability.
- Does not own: product UI, product DB tables, auth, or persistence policy for app records.

## Current Slice

- Shared operation-envelope runtime is in place.
- All extracted operations are exposed through `/v1/operations/{operation_name}`.
- Prompt ownership lives in `SKILL.md` plus Python prompt builders inside `learning-core`.
- Skill runtime code lives under `learning_core/skills/<skill>/scripts/main.py` and any
  skill-local helper modules live alongside it in `scripts/`.
- Public operations now route through a shared internal kernel that normalizes requests,
  resolves task profiles and response types, builds workflow-card previews, and executes
  through explicit bounded strategies.

## Runtime Model

`learning-core` now has one internal runtime vocabulary:

- `task_profiles`: what kind of job the request is asking for
- `response_types`: the typed artifact contract that must come back
- `workflow_cards`: bounded prompt and execution recipes
- `packs`: reusable domain context layered in by request metadata or task-specific selection
- `AgentKernel`: the shared preview/execute backbone used by the public operation routes

The public API is still operation-based.
Internally, those operations map onto the shared runtime layer.

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
  domain/
  observability/
  runtime/
  skills/
    activity_feedback/
      SKILL.md
      scripts/
        main.py
    activity_generate/
      SKILL.md
      packs/
        index.md
        math/
        chess/
      ui_components/
      ui_widgets/
      scripts/
        main.py
        policy.py
        schemas.py
        tooling.py
    widget_transition/
      SKILL.md
      scripts/
        main.py
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
    curriculum_update_propose/
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
    launch_plan_generate/
      SKILL.md
      scripts/
        main.py
    session_generate/
      SKILL.md
      scripts/
        main.py
    source_interpret/
      SKILL.md
      scripts/
        main.py
    session_evaluate/
      SKILL.md
      scripts/
        main.py
```

## API

- `GET /healthz`
- `GET /v1/runtime/status`
- `GET /v1/operations`
- `POST /v1/operations/{operation_name}/prompt-preview`
- `POST /v1/operations/{operation_name}/execute`

Internal orchestration helpers live behind the engine and are not the main public API.
The first internal source-entry chain currently available is `generate_from_source`, which composes:

1. `source_interpret`
2. `curriculum_generate`

`curriculum_generate` is the single curriculum-creation skill. It supports two explicit request modes:

- `source_entry`: source-first generation grounded in `source_interpret` output plus source text, packages, and files
- `conversation_intake`: conversation-first generation grounded in learner messages, goals, and pacing hints

The output is always one durable curriculum artifact. Opening-slice selection is handled separately by `launch_plan_generate`.

Current first-class operations:

- `activity_feedback`
- `activity_generate`
- `widget_transition`
- `session_generate`
- `source_interpret`
- `curriculum_intake`
- `copilot_chat`
- `curriculum_generate`
- `curriculum_revise`
- `launch_plan_generate`
- `progression_generate`
- `progression_revise`
- `session_evaluate`

## Design Rules

- No silent fallbacks.
- Unknown operation names fail immediately.
- Missing model/provider config fails immediately.
- Runtime/provider defaults do not live in code; define them in `.env.local`.
- Contract mismatches fail immediately.
- Product repos persist artifacts; `learning-core` returns typed artifacts, lineage, and traces.
- Product repos send structured request envelopes only. They do not send prompt fragments or raw system prompts.
- The legacy generic gateway surface is deleted. Apps call named operations only.
- Backend domain logic is canonical for engine-backed widgets. Frontend libraries are rendering helpers, not the source of truth.

## Adding Runtime Pieces

When adding a new bounded capability:

1. Add or reuse a `response_type`.
2. Add or reuse a `task_profile`.
3. Add a `workflow_card`.
4. Add any reusable `packs` or tool families it needs.
5. Map the public operation to the shared runtime in `learning_core/runtime/task_profiles.py`.

Keep task-specific prompts and validators close to the task.
Keep routing, preview, tracing, and policy in the shared runtime layer.
