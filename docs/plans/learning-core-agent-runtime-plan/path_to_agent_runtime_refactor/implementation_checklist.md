# Implementation Checklist

## Phase 0

- [x] Write a short ADR locking the migration invariants.
- [x] Confirm external operation routes stay stable during the first migration.
- [x] Confirm the kernel will be product-neutral and not homeschool-specific.
- [x] Define the target runtime directory map.
- [x] Define the current-operation to future-task-profile map.
- [x] List intentionally deferred items.

## Phase 1

- [x] Add `agent_kernel.py`.
- [x] Add shared request normalization.
- [x] Add shared preview generation path.
- [x] Add shared execution loop abstraction.
- [x] Add shared tool runtime abstraction.
- [x] Add shared finalization/validation hooks.
- [x] Add shared retry hooks.
- [x] Add shared trace assembly hooks.
- [x] Route one pilot operation through the kernel behind a flag.

## Phase 2

- [x] Create `response_types/` with initial modules.
- [x] Create task-profile registry.
- [x] Define operation-to-profile mapping.
- [x] Define default runtime behavior per task profile.
- [x] Update the kernel to resolve behavior from task profile + response type.

## Phase 3

- [x] Add `workflow_cards/`.
- [x] Add generic `packs/` layer or a clearly shared pack system.
- [x] Extract reusable pack concepts from `activity_generate`.
- [x] Implement at least one non-activity workflow card.
- [x] Make pack resolution explainable in traces.

## Phase 4

- [x] Add shared tool family registration.
- [x] Add shared policy model.
- [x] Add response-type validation.
- [x] Add task-specific validation hooks.
- [x] Add repair-path handling.
- [x] Add shared retry policy by failure class.
- [x] Add uniform trace shape.
- [x] Verify prompt preview includes runtime metadata.

## Phase 5

- [x] Migrate `session_generate`.
- [x] Migrate `activity_generate`.
- [x] Add parity and regression tests for both.
- [x] Migrate evaluation/proposal operations.
- [x] Migrate intake/planning/revision operations.
- [x] Migrate `copilot_chat` last.
- [ ] Delete duplicate runtime scaffolding from migrated operations.

## Phase 6

- [x] Add `source_interpret` profile.
- [x] Add bounded orchestration support.
- [x] Add `generate_from_source` flow if still needed.
- [x] Keep orchestration typed and bounded.
- [x] Keep any generic execute surface internal or experimental first.

## Phase 7

- [x] Roll operations to the kernel behind flags.
- [x] Run scenario suites and preview comparisons.
- [x] Inspect traces and repair behavior.
- [x] Update README and developer docs.
- [ ] Remove dead runtime plumbing.
- [x] Confirm adding a new capability now follows the new shared path.
