# Phase 0 Implementation Note

## Goal

Lock the migration boundary for the shared agent runtime refactor before code moves begin.

## Relevant repo files reviewed

- `README.md`
- `learning_core/api/app.py`
- `learning_core/runtime/engine.py`
- `learning_core/runtime/registry.py`
- `learning_core/runtime/skill.py`
- `learning_core/runtime/policy.py`
- `learning_core/contracts/operation.py`
- `learning_core/contracts/responses.py`
- `learning_core/contracts/session_plan.py`
- `learning_core/contracts/activity.py`
- `learning_core/contracts/evaluation.py`
- `learning_core/contracts/curriculum.py`
- `learning_core/contracts/progression.py`
- `learning_core/contracts/source_interpret.py`
- `learning_core/contracts/copilot.py`
- `learning_core/contracts/activity_feedback.py`
- `learning_core/contracts/widget_transition.py`
- `learning_core/skills/*/SKILL.md`
- `learning_core/skills/*/scripts/main.py`
- `learning_core/skills/activity_generate/execution_flow.md`
- `learning_core/skills/activity_generate/widget_engine_onboarding.md`

## Current runtime shape

- Public API is already operation-based: `POST /v1/operations/{operation_name}/execute` and `prompt-preview`.
- `AgentEngine` owns envelope parsing, prompt preview, provider runtime creation, and basic contract validation.
- Most operations are thin `StructuredOutputSkill` subclasses that only build prompts and then rely on `engine.run_structured_output(...)`.
- `copilot_chat` uses the shared text path.
- `activity_feedback` and `widget_transition` are deterministic-first hybrids.
- `activity_generate` is the strongest bounded-agent implementation but still carries its own tool loop, retries, pack selection, pack planning, semantic validation, and trace assembly.

## Invariants locked for this refactor

1. External operation routes stay stable during migration.
2. Operation envelopes remain structured. Frontends do not send raw prompt fragments.
3. Typed contracts stay first-class. Freeform text is not the default output model.
4. The shared kernel is product-neutral.
5. Product-specific framing belongs in structured request metadata and packs, not the kernel.
6. Durable domain state stays outside `learning-core`.
7. `activity_generate` is treated as the strongest bounded-runtime pattern, not as the whole architecture.

## Target runtime layout

```text
learning_core/
  runtime/
    agent_kernel.py
    execution_loop.py
    request_normalization.py
    task_profiles.py
    pack_resolution.py
    tool_runtime.py
    validation.py
    finalization.py
    retries.py
    traces.py
    preview.py
  response_types/
    ...
  workflow_cards/
    ...
  packs/
    ...
```

## Operation migration map

| Current operation | Task profile | Response type | Initial workflow card |
| --- | --- | --- | --- |
| `source_interpret` | `source_interpret` | `source_interpretation` | `source_interpret` |
| `session_generate` | `bounded_day_generation` | `lesson_draft` | `bounded_day_generation` |
| `activity_generate` | `adaptive_or_bounded_activity_generation` | `activity_spec` | `activity_generation` |
| `activity_feedback` | `activity_evaluation` | `evaluation` | `activity_evaluation` |
| `widget_transition` | `interactive_assistance` | `widget_transition` | `widget_transition` |
| `session_evaluate` | `session_synthesis` | `evaluation` | `session_synthesis` |
| `curriculum_update_propose` | `proposal_generation` | `proposal` | `proposal_generation` |
| `curriculum_intake` | `intake_dialogue` | `intake_turn` | `intake_dialogue` |
| `curriculum_generate` | `long_horizon_planning` | `curriculum_artifact` | `long_horizon_planning` |
| `curriculum_revise` | `artifact_revision` | `curriculum_artifact_revision` | `artifact_revision` |
| `progression_generate` | `long_horizon_planning` | `progression_artifact` | `progression_generation` |
| `progression_revise` | `artifact_revision` | `progression_artifact` | `artifact_revision` |
| `copilot_chat` | `interactive_assistance` | `summary` | `interactive_assistance` |

## Deliberately deferred in the first kernel rollout

- Replacing named operation routes with a single public generic execute endpoint
- Broad autonomous chaining
- Persistence or workflow-truth changes
- Homeschool-specific routing logic inside the kernel
- Unrestricted write tools

## Phase 0 execution

- Add this note as the migration ADR for the runtime refactor.
- Use it as the contract for phase-by-phase implementation and cleanup.
