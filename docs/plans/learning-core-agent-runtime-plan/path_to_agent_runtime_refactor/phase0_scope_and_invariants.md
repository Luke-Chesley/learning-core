# Phase 0: Scope And Invariants

## Objective

Lock the refactor boundary before implementation starts.

The main risk in this project is not technical difficulty. The main risk is architectural overreach:

- collapsing the public API too early
- hiding product distinctions inside one giant prompt
- hard-coding homeschool assumptions into the kernel
- breaking the current strict operation/contract behavior

This phase exists to prevent that.

## Why This Phase Matters

The current system already has a working headless service shape:

- shared operation-envelope runtime
- named operations exposed through `/v1/operations/{operation_name}`
- strict failure on unknown operations and contract mismatches
- skill-local `SKILL.md` plus Python runtime helpers
- strong bounded behavior in `activity_generate`

That is a good base. The refactor should preserve the good parts while reducing duplicated runtime scaffolding.

## Decisions To Lock

### 1. Internal Unification, External Stability

For the first migration, keep the external operation model:

- `POST /v1/operations/{operation_name}/execute`
- `POST /v1/operations/{operation_name}/prompt-preview`

Do not replace these with one generic public endpoint yet.

### 2. One Runtime, Not One Prompt

The singular thing is the runtime architecture:

- execution loop
- tool runtime
- validation/finalization
- retries
- traces
- policy
- pack resolution

The singular thing is **not** the prompt.

### 3. Product Neutral Core

The kernel must be product-neutral.

It may know about:

- task profile
- response type
- workflow mode
- template
- context bundle
- autonomy tier
- packs
- tool families

It must not know about:

- homeschool page names
- specific app routes
- one product's onboarding copy
- one product's database model

### 4. Frontend-Supplied Context Wins

The frontend or calling product is responsible for passing the product-specific framing:

- template: `homeschool`, `tutoring_practice`, `classroom_support`, `workforce_onboarding`, `certification_prep`, `self_guided`
- workflow mode: `family_guided`, `educator_led`, `manager_led`, `cohort_based`, `self_guided`
- surface: `onboarding`, `today`, `planning`, `reporting`, `copilot`
- actor role: `adult`, `educator`, `manager`, `learner`, `coach`

The runtime should use these as routing signals, not infer them from homeschool-specific assumptions.

### 5. Contracts Stay First-Class

Every major output still needs a typed contract.

Examples:

- intake turn
- curriculum artifact
- progression artifact
- lesson draft
- activity artifact
- proposal
- evaluation summary
- reporting summary

Do not allow freeform text to become the default output type.

## Required Deliverables

- a short ADR or design note locking the invariants above
- a target directory map for the new runtime layout
- a migration map from current operations to future task profiles and response types
- a list of things intentionally deferred

## Current Operation To Future Runtime Map

| Current operation | Likely task profile | Primary response type | Notes |
| --- | --- | --- | --- |
| `curriculum_intake` | `source_interpret` or `intake_dialogue` | `intake_turn` or `source_interpretation` | May eventually split into two profiles |
| `curriculum_generate` | `long_horizon_planning` | `curriculum_artifact` | Keep explicit for now |
| `curriculum_revise` | `artifact_revision` | `curriculum_artifact` | Revision semantics stay bounded |
| `progression_generate` | `bounded_or_long_horizon_planning` | `progression_artifact` | May later merge with planning card resolution |
| `progression_revise` | `artifact_revision` | `progression_artifact` | Preserve reviewability |
| `session_generate` | `bounded_day_generation` | `lesson_draft` | This should become one of the primary paths |
| `activity_generate` | `adaptive_or_bounded_activity_generation` | `activity_spec` | Treat as the gold-standard implementation shape |
| `activity_feedback` | `activity_evaluation` | `evaluation` or `summary` | Keep bounded |
| `session_evaluate` | `session_synthesis` | `evaluation` or `summary` | Core future event-driven agent path |
| `curriculum_update_propose` | `proposal_generation` | `proposal` | Approval aware |
| `copilot_chat` | `interactive_assistance` | `summary` or `proposal` | Keep distinct from write-heavy flows |

## Deferred Items

Do not do these in Phase 0 or 1:

- one public `/v1/agent/execute` replacing all routes
- arbitrary autonomous chaining across the whole system
- generalized background scheduler/orchestrator rewrite
- product persistence redesign
- homeschool-specific policy branches in the kernel

## Success Criteria

Phase 0 is done when an implementation agent can answer all of these clearly:

- What stays stable externally?
- What becomes shared internally?
- What remains typed and explicit?
- Where does product-specific context belong?
- What is deliberately not being built yet?
