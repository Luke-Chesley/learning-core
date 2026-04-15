# Implementation Checklist

## Phase 0

- [ ] Write a short ADR locking the migration invariants.
- [ ] Confirm external operation routes stay stable during the first migration.
- [ ] Confirm the kernel will be product-neutral and not homeschool-specific.
- [ ] Define the target runtime directory map.
- [ ] Define the current-operation to future-task-profile map.
- [ ] List intentionally deferred items.

## Phase 1

- [ ] Add `agent_kernel.py`.
- [ ] Add shared request normalization.
- [ ] Add shared preview generation path.
- [ ] Add shared execution loop abstraction.
- [ ] Add shared tool runtime abstraction.
- [ ] Add shared finalization/validation hooks.
- [ ] Add shared retry hooks.
- [ ] Add shared trace assembly hooks.
- [ ] Route one pilot operation through the kernel behind a flag.

## Phase 2

- [ ] Create `response_types/` with initial modules.
- [ ] Create task-profile registry.
- [ ] Define operation-to-profile mapping.
- [ ] Define default runtime behavior per task profile.
- [ ] Update the kernel to resolve behavior from task profile + response type.

## Phase 3

- [ ] Add `workflow_cards/`.
- [ ] Add generic `packs/` layer or a clearly shared pack system.
- [ ] Extract reusable pack concepts from `activity_generate`.
- [ ] Implement at least one non-activity workflow card.
- [ ] Make pack resolution explainable in traces.

## Phase 4

- [ ] Add shared tool family registration.
- [ ] Add shared policy model.
- [ ] Add response-type validation.
- [ ] Add task-specific validation hooks.
- [ ] Add repair-path handling.
- [ ] Add shared retry policy by failure class.
- [ ] Add uniform trace shape.
- [ ] Verify prompt preview includes runtime metadata.

## Phase 5

- [ ] Migrate `session_generate`.
- [ ] Migrate `activity_generate`.
- [ ] Add parity and regression tests for both.
- [ ] Migrate evaluation/proposal operations.
- [ ] Migrate intake/planning/revision operations.
- [ ] Migrate `copilot_chat` last.
- [ ] Delete duplicate runtime scaffolding from migrated operations.

## Phase 6

- [ ] Add `source_interpret` profile.
- [ ] Add bounded orchestration support.
- [ ] Add `generate_from_source` flow if still needed.
- [ ] Keep orchestration typed and bounded.
- [ ] Keep any generic execute surface internal or experimental first.

## Phase 7

- [ ] Roll operations to the kernel behind flags.
- [ ] Run scenario suites and preview comparisons.
- [ ] Inspect traces and repair behavior.
- [ ] Update README and developer docs.
- [ ] Remove dead runtime plumbing.
- [ ] Confirm adding a new capability now follows the new shared path.
