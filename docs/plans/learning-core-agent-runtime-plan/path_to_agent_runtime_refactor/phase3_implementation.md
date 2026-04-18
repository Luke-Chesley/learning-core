# Phase 3 Implementation Note

## Goal

Introduce first-class workflow cards and a reusable pack layer.

## Relevant files reviewed

- `learning_core/skills/activity_generate/execution_flow.md`
- `learning_core/skills/activity_generate/widget_engine_onboarding.md`
- `learning_core/skills/activity_generate/packs/*`
- `learning_core/skills/session_generate/SKILL.md`

## Implemented

### Workflow cards

Added `learning_core/workflow_cards/` with:

- `base.py`
- `registry.py`

The first card set wraps the existing prompt builders rather than rewriting prompts:

- `bounded_day_generation`
- `source_interpret`
- `session_synthesis`
- `proposal_generation`
- `curriculum_intake`
- `long_horizon_planning`
- `artifact_revision`
- `activity_generation`
- `activity_evaluation`
- `widget_transition`
- `interactive_assistance`

### Packs

Added `learning_core/packs/` as the shared pack layer.

Current shared packs:

- `domains/homeschool`

Current migration bridge:

- `runtime/pack_resolution.py` resolves the generic domain pack
- `activity_generate` also contributes its existing subject packs through the shared pack-resolution path for traceability

### Non-activity consumption

`session_generate` now resolves through the shared card + pack path and receives the generic homeschool domain pack in preview metadata.

## Design choice

This phase intentionally bridges the existing `activity_generate` pack system into the new shared layer instead of moving every pack file in one rewrite.
