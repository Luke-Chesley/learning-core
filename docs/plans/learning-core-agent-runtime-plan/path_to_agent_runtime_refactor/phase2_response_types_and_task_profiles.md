# Phase 2: Response Types And Task Profiles

## Objective

Create the shared vocabulary that lets the kernel stay generic while tasks remain bounded.

This phase defines two core abstractions:

- **response types**: what kind of typed artifact must come back
- **task profiles**: what kind of job is being performed

These are the two most important anti-chaos boundaries in the refactor.

## Why This Phase Matters

If the kernel becomes generic but tasks are not explicitly typed, the system will drift toward one mushy agent.

If response types are explicit and task profiles are explicit, then the kernel can be shared without losing product clarity.

## Response Types

Create a central `learning_core/response_types/` module.

### Initial response types

```text
response_types/
  intake_turn.py
  curriculum_artifact.py
  progression_artifact.py
  lesson_draft.py
  activity_spec.py
  proposal.py
  evaluation.py
  summary.py
```

Each response type should define:

- output schema / contract
- parser
- validator
- finalizer hooks if needed
- optional preview metadata

### Design rule

Response types are generic learning-ops outputs, not homeschool screens.

Good examples:

- lesson draft
- proposal
- evaluation summary
- curriculum artifact

Bad examples:

- homeschool today card
- parent home panel output
- weekly homeschool record PDF

Those product-specific shapes belong in the app or in reporting packs above the core response type layer.

## Task Profiles

Create a central `learning_core/runtime/task_profiles.py` or similar registry.

### Initial task profiles

- `intake_dialogue`
- `source_interpret`
- `long_horizon_planning`
- `bounded_day_generation`
- `weekly_expansion`
- `adaptive_or_bounded_activity_generation`
- `activity_evaluation`
- `session_synthesis`
- `proposal_generation`
- `report_generation`
- `interactive_assistance`
- `artifact_revision`

### What a task profile controls

A task profile should define:

- default response type(s)
- tool family eligibility
- latency class
- retry policy
- pack resolution strategy
- preview shape
- whether chaining is allowed
- whether approval semantics matter
- whether the runtime prefers single-pass or agentic loop mode

### Example

`bounded_day_generation` might default to:

- response type: `lesson_draft`
- latency class: `interactive`
- tools: read-only context tools + limited pack docs
- runtime mode: single-pass unless pack tools are required
- retry policy: contract-parse + one repair attempt

`session_synthesis` might default to:

- response type: `evaluation` or `summary`
- latency class: `background`
- tools: evidence read tools + synthesis tools
- runtime mode: bounded loop
- approval required: false for draft output, true if operational proposal is emitted

## Operation Mapping Layer

Keep an explicit mapping from current public operations to runtime task profiles and response types.

This may live in a registry like:

```python
OPERATION_RUNTIME_MAP = {
    "session_generate": {
        "task_profile": "bounded_day_generation",
        "response_type": "lesson_draft",
    },
    ...
}
```

Do not make the kernel infer everything from operation names implicitly.

## Frontend-Supplied Intent

The frontend should be able to shape execution without hard-coding a homeschool-only runtime.

Examples of useful request fields:

- `template`
- `workflow_mode`
- `surface`
- `actor_role`
- `autonomy_tier`
- `latency_class`
- `pack_hints`
- `response_type_override` when allowed

The frontend should **not** pass raw prompt fragments.

## Recommended Contract

For migrated operations, standardize on a richer internal request metadata bundle even if the external public API stays the same for now.

Example internal normalized fields:

```json
{
  "task_profile": "bounded_day_generation",
  "requested_response_type": "lesson_draft",
  "template": "homeschool",
  "workflow_mode": "family_guided",
  "surface": "onboarding",
  "actor_role": "adult",
  "autonomy_tier": "draft",
  "latency_class": "interactive",
  "pack_hints": ["homeschool", "reading"]
}
```

## Out Of Scope

- full generic execute endpoint
- large-scale prompt rewrites
- tool implementation
- event orchestration

## Success Criteria

Phase 2 is complete when:

- response types exist as first-class modules
- task profiles exist as first-class runtime definitions
- current operations can be mapped onto those abstractions clearly
- the kernel can use task profiles and response types to decide execution behavior
- the vocabulary is generic enough to support future non-homeschool products
