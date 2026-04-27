# Path To Agent Runtime Refactor

## Purpose

This folder is the working plan for refactoring `learning-core` from a collection of mostly separate operation skills into a unified agentic runtime with:

- one execution kernel
- one tool-calling model
- one validation/finalization pipeline
- one trace/audit model
- one policy model
- one pack resolution model
- many typed response contracts
- many bounded workflow cards
- many bounded task profiles

The goal is **not** to replace the current system with one giant super-prompt.
The goal is **not** to redesign `learning-core` around homeschooling only.
The goal is to create a general learning-ops runtime that can serve homeschooling, tutoring, classroom support, workforce onboarding, certification prep, and future surfaces through the same internal architecture.

This plan should be read alongside:

- the repo's current README and operation model
- the platform architecture direction in `Agentic Platform Architecture`
- the existing deployment plans in `homeschool-v2`

## Core Recommendation

Refactor toward:

- **single runtime internally**
- **multiple bounded capabilities externally**

That means:

- keep app-facing named operations during the migration
- unify the internal execution model under a shared kernel
- preserve typed contracts and explicit failure semantics
- preserve product control boundaries and approval states
- keep domain records canonical outside `learning-core`

## What This Refactor Must Achieve

1. Remove duplicated runtime plumbing across skills.
2. Keep output contracts explicit and strict.
3. Preserve or improve observability, traces, and contract validation.
4. Make it easy to add new bounded capabilities without inventing a new execution model each time.
5. Support frontend-triggered flows where the frontend specifies context, intent, and output needs without `learning-core` becoming homeschool-specific.
6. Prepare for future internal chaining such as:
   - source interpretation
   - source-entry curriculum generation
   - session generation
   - activity generation
   - evaluation
   - reporting
7. Reuse the strongest current pattern: the bounded, policy-heavy, pack-aware style already present in `activity_generate`.

## Non-Goals

- No broad rewrite of all product behavior around a single generic `/agent/run` endpoint in phase 1.
- No rewrite of `homeschool-v2` to pass raw prompts.
- No migration of product persistence or workflow truth into `learning-core`.
- No homeschool-only abstractions at the kernel level.
- No fully autonomous planning system with unrestricted writes.

## Architectural Rules

1. Durable domain records remain canonical outside `learning-core`.
2. `learning-core` returns typed artifacts, traces, lineage, and bounded proposals.
3. Frontends pass structured context, workflow mode, template, and constraints.
4. Task routing is based on explicit request intent plus runtime decisioning, not vague chat-only behavior.
5. Skills become instances of a shared runtime pattern, not one-off implementations.
6. Homeschool is a pack/template choice, not the core architecture.

## Target Shape

```text
learning_core/
  runtime/
    agent_kernel.py
    execution_loop.py
    tool_runtime.py
    validation.py
    traces.py
    retries.py
    policy.py
    task_profiles.py
    pack_resolution.py
    finalization.py
  response_types/
    lesson_draft.py
    teaching_guide_artifact.py
    activity_spec.py
    intake_turn.py
    curriculum_artifact.py
    proposal.py
    evaluation.py
    summary.py
  workflow_cards/
    onboarding_intake/
    bounded_day_generation/
    teaching_support/
    long_horizon_planning/
    session_synthesis/
    reporting/
  packs/
    domains/
      homeschool/
      tutoring/
      workforce/
    subjects/
      math/
      chess/
      reading/
      writing/
      science/
    interactions/
      widgets/
      assessment_styles/
      evidence_patterns/
  tools/
    read_context.py
    read_pack_docs.py
    draft_artifact.py
    propose_adjustment.py
    synthesize_evidence.py
    create_recommendation.py
  skills/
    ... thin operation wrappers over the shared runtime ...
```

## Migration Principle

Do not collapse everything at once.

The safe path is:

1. build the kernel
2. define response types and task profiles
3. migrate one or two operations first
4. validate parity
5. migrate the rest
6. add higher-order chaining only after the base runtime is stable

## Phase Order

- Phase 0: Lock refactor scope and invariants
- Phase 1: Build the shared agent kernel
- Phase 2: Introduce response types and task profiles
- Phase 3: Introduce workflow cards and generic pack resolution
- Phase 4: Introduce generic tools, policy, retries, traces, and validation
- Phase 5: Migrate existing operations onto the shared runtime
- Phase 6: Add bounded orchestration flows and optional generic execute surface
- Phase 7: App integration, rollout, and cleanup

## Deliverables In This Folder

- `phase0_scope_and_invariants.md`
- `phase1_shared_agent_kernel.md`
- `phase2_response_types_and_task_profiles.md`
- `phase3_workflow_cards_and_packs.md`
- `phase4_tools_policy_validation_and_traces.md`
- `phase5_operation_migration.md`
- `phase6_orchestration_and_generic_execute.md`
- `phase7_rollout_and_cleanup.md`
- `implementation_checklist.md`
- `agent_handoff.md`

## Exit Condition

This refactor is complete when:

- the major existing operations are running through one shared execution kernel
- each operation still returns strict typed artifacts
- activity generation retains its bounded behavior and pack logic
- new bounded capabilities can be added through task profiles + workflow cards + packs instead of bespoke runtime code
- the frontend can trigger different flows through structured context without `learning-core` being hard-coded around homeschool screens
