# Phase 5: Operation Migration

## Objective

Move existing public operations onto the shared runtime without breaking contract compatibility.

This phase should be incremental, test-heavy, and boring.

## Migration Rule

Do not migrate all operations in one pass.

Use an ordered sequence that starts with the highest-leverage, best-understood operations.

## Recommended Migration Order

### Wave 1

- `session_generate`
- `activity_generate`

Why:

- they are central to the activation/product wow path
- they cover both simpler generation and richer pack-aware generation
- they will exercise the new kernel, tool runtime, validation, and pack resolution meaningfully

### Wave 2

- `session_evaluate`
- `activity_feedback`
- `curriculum_update_propose`

Why:

- these naturally benefit from shared evaluation/proposal response types
- they sit closer to future event-driven agent loops

### Wave 3

- `curriculum_intake`
- `curriculum_generate`
- `progression_generate`
- `curriculum_revise`
- `progression_revise`

Why:

- these are important, but they may need more rethinking around `source_interpret`, source-entry curriculum flows, and revision flows
- they should migrate after the runtime is already proven

### Wave 4

- `copilot_chat`

Why:

- it is the least important for proving the refactor
- it may need looser interaction patterns and should not distort the shared runtime too early

## Operation Wrapper Pattern

Each existing public operation should become a thin wrapper that:

1. validates the public request envelope
2. maps to a runtime request
3. selects task profile + response type + workflow card + pack hints
4. invokes the kernel
5. adapts the kernel result back to the public response shape if needed

The wrapper should contain as little logic as possible.

## Parity Requirements

For each migrated operation, verify:

- public API contract still works
- prompt preview still works
- typed contract still validates
- traces remain available
- failure semantics remain strict
- latency stays acceptable

## Testing Requirements

Every migrated operation should have:

- request normalization tests
- preview tests
- contract validation tests
- error-path tests
- parity tests against representative old behavior

For `activity_generate`, add pack and validator regression coverage.

## Suggested Migration Mechanics

- feature-flag new runtime path per operation
- keep old implementation reachable during migration
- log runtime comparison metadata where useful
- switch default only after parity confidence is high

## Cleanup Rule

After an operation is successfully migrated:

- delete duplicate runtime plumbing from the old skill path
- keep task-specific prompt/policy/content where it belongs
- do not leave two permanent competing execution stacks

## Out Of Scope

- generic endpoint as the main interface
- big pack expansion
- product routing changes in `homeschool-v2`

## Success Criteria

Phase 5 is complete when:

- the core public operations run through one shared kernel
- wrappers are thin and explicit
- activity generation keeps its bounded pack-aware behavior
- adding a new operation no longer requires inventing a bespoke runtime pattern
