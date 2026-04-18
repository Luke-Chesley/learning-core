# Phase 5 Implementation Note

## Goal

Move public operations onto the shared runtime without changing the public API.

## Implemented migration state

All public operations now enter through:

1. request normalization
2. task-profile / response-type / workflow-card resolution
3. kernel preview or execute routing

### Shared structured strategy

These operations now use the kernel plus the shared structured-output provider path:

- `session_generate`
- `source_interpret`
- `curriculum_intake`
- `progression_generate`
- `progression_revise`
- `session_evaluate`
- `curriculum_update_propose`

### Shared text strategy

- `copilot_chat`

### Explicit custom strategies behind the kernel

These operations are now kernel-routed but still execute through explicit task-specific logic because that logic is materially richer than the generic path:

- `activity_generate`
- `activity_feedback`
- `widget_transition`
- `curriculum_generate`
- `curriculum_revise`

## Why this still counts as migration

The public engine no longer decides execution by bespoke top-level branching.
The kernel now owns normalization, routing, preview metadata, and the execution-strategy decision.
The remaining custom logic is explicit and bounded behind that runtime contract.
