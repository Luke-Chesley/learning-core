# Phase 6: Bounded Orchestration And Optional Generic Execute

## Objective

Once the shared runtime is stable, add bounded multi-step orchestration for higher-level flows.

This phase is where the runtime begins to feel more agentic, but it should still stay bounded and typed.

## Why This Phase Comes Later

If orchestration is added before the kernel and migration are stable, debugging becomes miserable.

The runtime first needs:

- stable task profiles
- stable response types
- stable tool permissions
- stable traces

Only then should it start chaining tasks.

## What Orchestration Means Here

Orchestration does **not** mean a limitless super-agent.

It means the runtime can execute a short bounded chain such as:

1. interpret source
2. choose horizon
3. generate lesson draft
4. generate activity from the lesson draft
5. return both artifacts with traces

This is exactly the kind of flow your onboarding/product activation needs, but it should be built on top of the stable kernel rather than by bypassing it.

## New Internal Profiles To Add

- `source_interpret`
- `curriculum_generate`
- `generate_from_source`

These can be implemented as runtime-level orchestrations over existing or new lower-level task profiles.

## Generic Execute Surface

A generic execute surface may be useful, but it should start as:

- internal-only
- experimental
- studio/debug/tooling facing

Examples:

- `/v1/runtime/execute`
- `/v1/agent/execute`

But do **not** make it the only or primary public API yet.

## Generic Execute Request Shape

If added, it should be explicit and typed.

Example:

```json
{
  "task_profile": "generate_from_source",
  "requested_response_types": ["lesson_draft", "activity_spec"],
  "template": "homeschool",
  "workflow_mode": "family_guided",
  "surface": "onboarding",
  "actor_role": "adult",
  "autonomy_tier": "draft",
  "context_bundle": {...},
  "pack_hints": ["reading"],
  "input_assets": [...],
  "constraints": {...}
}
```

Note that even here the request is still structured and typed.

## Orchestration Guardrails

- maximum chain length
- explicit intermediate artifacts
- explicit failure semantics
- visible traces for substeps
- no unrestricted durable writes
- no hidden application of major plan changes

## First Orchestration Candidate

The best first orchestration is the activation flow discussed in product planning:

- parent gives typed, pasted, imaged, or file-based source material
- runtime interprets it
- runtime generates a source-entry curriculum launch grounded in that interpretation
- runtime returns a typed curriculum artifact with launch planning metadata
- runtime optionally chains session or activity generation after the launch is accepted

This is a good fit because it is highly visible, product-critical, and naturally bounded.

## Out Of Scope

- broad autonomous background workers
- organization-wide recommendation engines
- long-running tutoring personas

## Success Criteria

Phase 6 is complete when:

- the runtime can orchestrate a bounded multi-step flow
- each substep remains typed and traced
- the frontend can call a higher-order flow without losing explicitness
- the system still resists becoming a giant vague super-agent
