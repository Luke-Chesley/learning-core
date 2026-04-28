# learning-core

`learning-core` is the headless Python AI runtime behind `homeschool-v2`.

For the current closed-beta product, it turns structured homeschool product context into bounded, typed artifacts.
It does not own UI, auth, product persistence, or direct product mutations.

## Current Product Context

- Primary consuming app: `../homeschool-v2`
- Current wedge: help a parent-led K-8 homeschool parent move from source material to parent explanation, teachable lesson, guided questions, practice, assessment, and state-aware/export-friendly records.
- Billing is out of scope for the current launch-prep work.

## Read This First

- Current operational source of truth: `docs/CURRENT_PRODUCT_AND_RUNTIME_MODEL.md`
- Source taxonomy and horizon notes: `docs/source-taxonomy-model.md`
- Launch eval fixtures and rubric: `tests/fixtures/launch_eval/scenarios.json`, `tests/test_launch_eval_fixtures.py`
- `docs/plans/` is implementation history and future planning, not the operational guide for the current beta product.

## Scope

- Owns: named operations, contracts, prompt and `SKILL.md` loading, workflow semantics, validation, prompt previews, model execution, lineage, traces, and observability.
- Does not own: product UI, product DB tables, auth, or app-side approval and mutation policy.

## Current Generation Chain

At the product level, `homeschool-v2` currently treats this repo as the AI side of a homeschool-specific flow:

1. `source_interpret` classifies source entry and recommends the safest opening approach.
2. `curriculum_generate` creates the durable curriculum artifact.
3. Opening-window and day-1 handoff are downstream planning concerns. They are not part of the canonical `curriculum_generate` artifact contract.
4. `progression_generate` helps turn the curriculum into schedulable order for the app-side planning system.
5. `session_generate` creates a bounded lesson draft for a specific day or slot.
6. `teaching_guide_generate` returns a parent-facing teaching support artifact for explanation, guided questions, practice, quick checks, and repair support.
7. `activity_generate` creates lesson-scoped learner activities.
8. `copilot_chat` provides grounded adult-facing assistance. It may summarize or propose, but the app must validate and apply any real mutation itself.

`curriculum_generate` is the single curriculum-creation skill.
It supports two explicit request modes:

- `source_entry`: source-first generation grounded in `source_interpret` output plus source text, packages, and files
- `conversation_intake`: conversation-first generation grounded in learner messages, goals, and pacing hints

The output is one durable curriculum artifact.
That artifact is a teachable content map, not just a broad skill outline:

- `contentAnchors[]` names the facts, examples, terms, source sections, procedures, artifacts, problems, or historical examples to teach.
- `teachableItems[]` turns those anchors into parent-teachable slices with focus questions, vocabulary, learner outcomes, assessment cues, misconceptions, and notes.
- `skills[]` is still the authoritative route/planning handle, but each skill must be concrete and grounded in content anchors or teachable items.
- `units[].skillIds` links units to those skills.
- `planningModel` tells the app whether this is a single lesson, flexible content map, authored source sequence, reference map, or explicit `session_sequence`.
- `deliverySequence[]` is required when the source has an explicit session/timebox sequence; for session-counted plans it has one item per session.

The model does not author a second nested curriculum tree or canonical path refs.
`homeschool-v2` derives the persisted document tree and canonical `skillRefs` after validation, then carries the content map into route items, Today, and `session_generate`.

The app owns import, persistence, progression handoff, and opening-window or day-1 flow selection.

## Runtime Model

`learning-core` uses one internal runtime vocabulary:

- `task_profiles`
  What kind of job the request is asking for.
- `response_types`
  The typed artifact contract that must come back.
- `workflow_cards`
  Bounded prompt and execution recipes.
- `packs`
  Reusable domain context layered in by request metadata or task-specific selection.
- `AgentKernel`
  The shared preview and execute backbone used by the public operation routes.

The public API remains operation-based.
Internally, those operations map onto the shared runtime layer.

## Current First-Class Operations

| Operation | Current role | Task profile | Response type |
| --- | --- | --- | --- |
| `source_interpret` | classify source entry and opening horizon | `source_interpret` | `source_interpretation` |
| `curriculum_generate` | create the durable curriculum artifact | `long_horizon_planning` | `curriculum_artifact` |
| `progression_generate` | produce schedulable curriculum ordering and structure | `long_horizon_planning` | `progression_artifact` |
| `session_generate` | create a bounded day lesson draft | `bounded_day_generation` | `lesson_draft` |
| `teaching_guide_generate` | create parent-facing teaching support for the current lesson | `teaching_support` | `teaching_guide_artifact` |
| `activity_generate` | create lesson-scoped learner activities | `adaptive_or_bounded_activity_generation` | `activity_spec` |
| `activity_feedback` | return bounded component-level learner-feedback responses | `activity_evaluation` | `activity_feedback` |
| `widget_transition` | execute deterministic widget transitions | `interactive_assistance` | `widget_transition` |
| `curriculum_intake` | handle intake dialogue turns | `intake_dialogue` | `intake_turn` |
| `curriculum_revise` | revise a curriculum artifact | `artifact_revision` | `curriculum_artifact_revision` |
| `progression_revise` | revise progression structure | `artifact_revision` | `progression_artifact` |
| `session_evaluate` | synthesize lesson/session outcomes | `session_synthesis` | `evaluation` |
| `copilot_chat` | grounded parent-facing assistance | `interactive_assistance` | `summary` |

Registered but not part of the current canonical product chain:

- `launch_plan_generate`
  still exists in the runtime for bounded opening-slice generation, but do not treat it as proof that every current curriculum flow returns or persists `launchPlan`; when used, it returns canonical `openingSkillRefs` only and the app derives owning unit refs after validation.

## Copilot Boundary

`copilot_chat` is not allowed to mutate product state directly.

- The app sends structured learner, curriculum, daily, and weekly context.
- `learning-core` returns bounded chat output grounded in that context.
- Any action proposal must stay explicit, typed, and app-approved.
- The app owns approval, dispatch, persistence, and failure handling.

If a Copilot artifact and the product state disagree, the product state wins.

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
   - provider credential and base-url vars for the selected backend
6. Run the API:
   - `uv run learning-core`

The service defaults to `http://127.0.0.1:8000`.
`learning-core` auto-loads `.env` and `.env.local` from the repo root without requiring you to `source` them first.

## Provider Logs

- Every provider request and response exchange is written to `logs/YYYY-MM-DD/`.
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
    teaching_guide_generate/
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
    curriculum_update_propose/
      SKILL.md
      scripts/
        main.py
    launch_plan_generate/
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
    session_evaluate/
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
```

## API

- `GET /healthz`
- `GET /v1/runtime/status`
- `GET /v1/operations`
- `POST /v1/operations/{operation_name}/prompt-preview`
- `POST /v1/operations/{operation_name}/execute`

Internal orchestration helpers live behind the engine and are not the main public API.

## Design Rules

- No silent fallbacks.
- Unknown operation names fail immediately.
- Missing model or provider config fails immediately.
- Runtime and provider defaults do not live in code; define them in `.env.local`.
- Contract mismatches fail immediately.
- Product repos persist artifacts; `learning-core` returns typed artifacts, lineage, and traces.
- Product repos send structured request envelopes only. They do not send prompt fragments or raw system prompts.
- `learning-core` never mutates app state directly.
- Teaching Guide artifacts are generated support only. The app owns persistence, supersession, parent approval, and any saved notes, evidence, or records.
- `activity_feedback` remains bounded component-level learner feedback; Teaching Guide and parent review support can be richer, adult-facing repair guidance, but still returns artifacts only.
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
