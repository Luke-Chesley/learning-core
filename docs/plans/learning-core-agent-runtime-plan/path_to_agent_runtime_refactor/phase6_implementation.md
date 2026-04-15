# Phase 6 Implementation Note

## Goal

Add a bounded internal orchestration flow built on top of the shared runtime.

## Implemented

Added `AgentEngine.execute_generate_from_source(...)` as an internal orchestration helper.

Current bounded chain:

1. `source_interpret`
2. `bounded_plan_generate`

The helper:

- keeps the public operation API unchanged
- reuses the same kernel-routed operations internally
- returns a typed `bounded_plan_generate` response
- records orchestration substeps in `trace.agent_trace`

## Why this is the right first orchestration

- It is short and bounded.
- It exercises the new shared runtime rather than bypassing it.
- It matches the refactor plan’s source-to-plan activation flow.
