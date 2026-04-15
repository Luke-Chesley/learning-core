# Phase 2 Implementation Note

## Goal

Add the shared runtime vocabulary that lets one kernel serve many bounded capabilities.

## Relevant files reviewed

- `learning_core/contracts/*.py`
- `learning_core/skills/*/scripts/main.py`
- `learning_core/runtime/task_profiles.py`

## Implemented

### Response types

Added first-class response-type modules under `learning_core/response_types/` for:

- `lesson_draft`
- `activity_spec`
- `activity_feedback`
- `evaluation`
- `proposal`
- `curriculum_artifact`
- `curriculum_artifact_revision`
- `progression_artifact`
- `intake_turn`
- `source_interpretation`
- `bounded_plan`
- `summary`
- `widget_transition`

Each response type now carries the contract model and execution mode metadata.

### Task profiles

Added `learning_core/runtime/task_profiles.py` with:

- task-profile registry
- operation-to-runtime mapping
- default runtime behavior per profile

The kernel now resolves:

- task profile
- response type
- workflow card
- execution strategy

from an explicit operation mapping instead of inferring behavior ad hoc.

## Why this cut is good enough

- The vocabulary is now generic and reusable.
- Existing public operations still stay explicit.
- The kernel can answer what kind of job the request is and what contract it must return.
