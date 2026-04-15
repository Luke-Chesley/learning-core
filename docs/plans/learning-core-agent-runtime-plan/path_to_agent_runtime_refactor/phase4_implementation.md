# Phase 4 Implementation Note

## Goal

Standardize the runtime mechanics that make the kernel inspectable and bounded.

## Relevant files reviewed

- `learning_core/runtime/policy.py`
- `learning_core/observability/traces.py`
- `learning_core/skills/activity_generate/scripts/main.py`
- `learning_core/runtime/tooling.py`

## Implemented

### Policy

Expanded `ExecutionPolicy` to carry:

- `runtime_mode`
- `autonomy_tier`
- `latency_class`
- `tool_families`
- `max_loop_steps`
- `repair_attempts`

### Tools

Added `learning_core/runtime/tool_runtime.py` with:

- explicit tool-family registry
- resolved tool-runtime plans
- shared metadata for allowed tools vs tool families

### Validation and traces

Added:

- `runtime/validation.py`
- `runtime/traces.py`
- richer preview metadata on `OperationPromptPreviewResponse`
- richer execution metadata on `ExecutionTrace`

Runtime previews and traces now surface:

- task profile
- response type
- workflow card
- runtime mode
- selected packs
- tool families

### Activity repair alignment

Adjusted the `activity_generate` schema-repair path to use a direct model repair call.
This matches the repo’s existing repair-test expectations while keeping pack-tool and semantic repairs on the bounded agent loop.
