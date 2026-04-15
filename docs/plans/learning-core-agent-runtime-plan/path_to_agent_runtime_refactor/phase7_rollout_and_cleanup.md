# Phase 7: Rollout And Cleanup

## Objective

Ship the new runtime safely, roll operations over in stages, and remove duplicate infrastructure.

## Rollout Strategy

### 1. Internal validation first

Before broad rollout:

- run contract parity checks
- run preview comparisons
- run scenario suites against key operations
- inspect traces and repair behavior

### 2. Per-operation feature flags

Enable new runtime paths behind operation-level flags.

Examples:

- `LEARNING_CORE_USE_KERNEL_FOR_SESSION_GENERATE`
- `LEARNING_CORE_USE_KERNEL_FOR_ACTIVITY_GENERATE`

### 3. Shadow comparisons where useful

For high-value operations, optionally run old and new paths against representative fixtures and compare:

- response validity
- response completeness
- trace quality
- latency

### 4. Remove duplicate plumbing aggressively once stable

After a migrated operation has proven stable:

- delete the old duplicated runtime code
- keep only task-specific behavior that still belongs with the operation/card/pack

## App Integration Guidance

This refactor should not force `homeschool-v2` into a homeschool-only contract shape.

Instead, app integration should gradually move toward sending richer structured metadata, such as:

- template
- workflow mode
- surface
- actor role
- autonomy tier
- pack hints
- source/input asset descriptors

That still leaves the app in control of product semantics while letting `learning-core` stay reusable.

## Documentation Requirements

At the end of rollout, update:

- `learning-core/README.md`
- operation list and runtime explanation
- prompt preview docs
- how to add a new task profile
- how to add a new response type
- how to add a new workflow card
- how to add a new pack
- how to add a new tool family

## Cleanup Rules

Remove:

- obsolete per-skill runtime boilerplate
- duplicate retry logic
- duplicate trace assembly logic
- duplicate contract-finalization plumbing

Keep:

- task-specific prompts
- pack content
- task-specific validators
- thin public operation wrappers

## Long-Term Outcome

After rollout, the system should feel like:

- one runtime engine
- one model/tool/trace/policy philosophy
- many bounded capabilities
- many typed artifacts
- many reusable packs

not:

- one giant prompt
- one giant endpoint
- one homeschool-specific code path

## Success Criteria

Phase 7 is complete when:

- the core operations run through the kernel by default
- the old duplicated runtime scaffolding is removed
- the README and developer docs explain the new mental model clearly
- new capabilities can be added by composing runtime pieces instead of inventing a new architecture each time
