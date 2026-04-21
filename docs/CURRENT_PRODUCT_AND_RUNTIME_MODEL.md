# Current Product And Runtime Model

> Status: this is the operational source of truth for the current `learning-core` role in the homeschool closed-beta product.
> Use this before older planning docs when you need the live runtime model.

## Current Product Wedge

`learning-core` currently serves a homeschool-first product.

The product wedge is:

1. bring what the parent already has
2. create a usable curriculum and opening window
3. reach Today fast
4. keep the week and records nearby

This repo should support that wedge directly.
Do not treat broader cross-domain positioning or billing work as the current launch target.

## What This Repo Owns

`learning-core` owns:

- named AI operations
- contracts and response validation
- prompt assembly and `SKILL.md` loading
- provider and model selection
- prompt previews, lineage, traces, and runtime observability
- bounded runtime semantics through task profiles, response types, workflow cards, and packs

`learning-core` does not own:

- product UI
- auth
- app-side persistence
- approval and application of product mutations

## Current Operation Chain

For the current product, the main chain is:

1. `source_interpret`
2. `curriculum_generate`
3. progression and planning handoff in the app
4. opening-window, day-1, and Today handoff in the app

Downstream operations then support bounded execution:

- `session_generate` for a specific lesson or day slice
- `activity_generate` for lesson-scoped learner activity generation
- `session_evaluate` for post-session synthesis
- `copilot_chat` for grounded parent-facing assistance

## Source Interpretation

`source_interpret` is interpretation only.

It owns:

- source kind classification
- entry strategy
- continuation mode
- delivery pattern
- recommended opening horizon

It does not own curriculum creation, lesson generation, or direct product mutation.

## Curriculum Creation

`curriculum_generate` is the canonical curriculum-creation skill.

It supports:

- `requestMode: "source_entry"`
- `requestMode: "conversation_intake"`

The output is one durable curriculum artifact.

Opening-window selection is downstream of the curriculum artifact.
Older docs sometimes describe `launchPlan` as if it were part of every `curriculum_generate` response, but that is not the current canonical contract.
`launch_plan_generate` still exists in the runtime, but it should be treated as a separate bounded operation, not the main product mental model.

## Runtime Vocabulary

The current runtime layer is organized around:

- `task_profiles`
  current execution intent such as `source_interpret`, `long_horizon_planning`, `bounded_day_generation`, and `interactive_assistance`
- `response_types`
  current contracts such as `source_interpretation`, `curriculum_artifact`, `lesson_draft`, `activity_spec`, and `summary`
- `workflow_cards`
  bounded prompt and execution recipes for the current task families
- `packs`
  reusable domain context for the skills that need extra grounding

This vocabulary is not generic architecture for its own sake.
It exists to keep the homeschool app boundary strict and predictable.

## Copilot Boundary

`copilot_chat` is bounded assistance.

Current rules:

- the app provides structured learner, curriculum, daily, and weekly context
- `learning-core` returns grounded Copilot output
- any action suggestion must stay explicit, typed, and bounded
- the app validates, approves, dispatches, and persists any real mutation

`learning-core` never gets direct authority to mutate product state.

## Deferred

These are not part of the current operational model:

- billing or Stripe-related behavior
- generic app-side prompt assembly
- frontends sending raw prompt fragments or provider instructions
- treating Copilot as an unrestricted write surface
- broader platform-generalization work that weakens the homeschool launch wedge

## Related Docs

Current-state references:

- `README.md`
- `docs/source-taxonomy-model.md`
- `../docs/architecture/README.md`
- `../docs/architecture/repo-interaction-map.md`

Historical or broader planning references:

- `docs/plans/`
- `../homeschool-v2/docs/VISION.md`
- `../homeschool-v2/docs/PRODUCT_IMPLEMENTATION_PLAN.md`
