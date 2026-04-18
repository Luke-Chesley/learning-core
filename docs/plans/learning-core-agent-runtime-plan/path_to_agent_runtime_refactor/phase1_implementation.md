# Phase 1 Implementation Note

## Goal

Introduce one shared internal execution kernel without breaking the existing public operation API.

## Relevant repo files reviewed before implementation

- `learning_core/runtime/engine.py`
- `learning_core/runtime/context.py`
- `learning_core/runtime/policy.py`
- `learning_core/runtime/providers.py`
- `learning_core/runtime/registry.py`
- `learning_core/runtime/skill.py`
- `learning_core/skills/base.py`
- `learning_core/skills/session_generate/scripts/main.py`
- `learning_core/skills/activity_generate/scripts/main.py`
- `learning_core/skills/activity_generate/execution_flow.md`

## Implementation decisions

1. Keep `AgentEngine` as the stable public entry point used by the API.
2. Add `AgentKernel` under `learning_core/runtime/agent_kernel.py`.
3. Normalize every request into a `RuntimeRequest` before preview/execute.
4. Preserve current prompt builders by routing workflow cards back through the existing skill classes.
5. Preserve the existing provider-path methods `run_structured_output(...)` and `run_text_output(...)` so current tests and monkeypatches stay valid.
6. Keep custom skills such as `activity_generate`, `activity_feedback`, and `widget_transition` executable through the kernel via explicit execution strategies while the shared abstractions settle.

## New runtime modules added in this phase

- `runtime/agent_kernel.py`
- `runtime/request_normalization.py`
- `runtime/task_profiles.py`
- `runtime/pack_resolution.py`
- `runtime/tool_runtime.py`
- `runtime/preview.py`
- `runtime/traces.py`
- `runtime/finalization.py`
- `runtime/validation.py`
- `runtime/retries.py`
- `runtime/execution_loop.py`

## Kernel shape implemented

- `AgentEngine.preview(...)` now:
  - validates the operation envelope
  - normalizes it into a `RuntimeRequest`
  - asks the kernel for the preview
  - returns the same public preview response plus runtime metadata

- `AgentEngine.execute(...)` now:
  - validates and normalizes the operation request
  - routes execution through the kernel
  - preserves the existing public response shape

## Pilot migration outcome

The first clean pilot path is the structured-output family:

- `session_generate`
- `source_interpret`
- `curriculum_intake`

These now flow through:

1. request normalization
2. task-profile resolution
3. workflow-card preview construction
4. kernel execution strategy selection
5. the existing shared structured-output provider path

## Why this is the right Phase 1 cut

- It adds one internal kernel immediately.
- It keeps the external API stable.
- It proves preview and execute can both route through shared runtime metadata.
- It does not force the richer `activity_generate` path into a premature rewrite.

## Verification run

Executed:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest \
  tests/test_api_operations.py \
  tests/test_skill_registry.py \
  tests/test_session_generate_lesson_shape.py \
  tests/test_source_interpret.py \
  tests/test_curriculum_generate.py
```

Result:

- `20 passed`
