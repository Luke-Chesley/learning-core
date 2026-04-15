# Agent Handoff: Refactor `learning-core` Into A Shared Agent Runtime

## What You Are Building

Refactor `learning-core` from a set of mostly separate skill runtimes into one shared internal agent runtime with:

- one execution kernel
- one tool-calling model
- one validation/finalization model
- one retry/policy/trace model
- many bounded task profiles
- many typed response types
- many reusable workflow cards and packs

## What You Are Not Building

Do **not** build:

- one giant super-prompt
- one unrestricted public `/agent/run` endpoint as the only API
- a homeschool-specific kernel
- a rewrite where frontends send raw prompt fragments
- an autonomous system with unrestricted writes

## Why This Matters

The current system already has strong foundations:

- named operations
- strict contract behavior
- operation-envelope execution
- pack-aware bounded activity generation

But runtime concerns are still too scattered across skills. This refactor should unify the runtime model without erasing the distinctions between curriculum generation, session generation, activity generation, evaluation, proposals, and chat.

## Critical Design Boundaries

1. Keep external operation routes stable during the first migration.
2. Keep typed contracts first-class.
3. Keep durable product state outside `learning-core`.
4. Keep homeschool-specific logic out of the kernel.
5. Let the frontend pass product-specific framing like template, workflow mode, and surface.
6. Treat `activity_generate` as the strongest current implementation pattern, not as the only pattern.

## Practical Guidance

### Product-neutral kernel

The kernel should understand generic execution concepts such as:

- task profile
- response type
- workflow mode
- template
- surface
- actor role
- autonomy tier
- pack hints
- tool families

The kernel should not understand:

- homeschool page names
- app route structure
- one product's UI copy

### Public API stability

Keep current public operations alive during migration.

Make them thin wrappers over the new kernel rather than replacing them all immediately.

### Migration order

1. `session_generate`
2. `activity_generate`
3. `session_evaluate`, `activity_feedback`, `curriculum_update_propose`
4. `curriculum_intake`, `curriculum_generate`, `progression_generate`, revisions
5. `copilot_chat`

## Expected Deliverables

- shared runtime modules under `learning_core/runtime/`
- first-class `response_types/`
- task-profile registry
- workflow-card registry
- reusable pack system or clearly shared pack layer
- migrated operations using thin wrappers
- updated README/docs
- removed duplicate runtime plumbing from migrated operations

## Quality Bar

Do not optimize for elegance at the expense of clarity.

Good output from this refactor should make it easier to answer:

- What kind of job is this request asking for?
- What type of output must come back?
- Which tools are allowed?
- Which packs influenced generation?
- Why did validation fail?
- What trace do we have for this run?

## First PR Suggestion

Make the first PR small and decisive:

- add the kernel skeleton
- add task profiles
- add response-type registry
- migrate `session_generate` behind a feature flag
- do not migrate everything at once

## Definition Of Done

This project is done when `learning-core` behaves like one coherent agentic runtime internally, while still exposing multiple bounded capabilities externally.
