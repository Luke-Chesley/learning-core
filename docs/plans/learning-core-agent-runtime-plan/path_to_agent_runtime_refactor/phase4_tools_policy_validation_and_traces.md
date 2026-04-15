# Phase 4: Tools, Policy, Validation, Retries, And Traces

## Objective

Standardize the operational mechanics that make the kernel trustworthy:

- tool exposure and logging
- policy enforcement
- validation and repair
- retry strategy
- traces and lineage

This phase is where the refactor either becomes production-grade or turns into a black box.

## Why This Phase Matters

A unified runtime is only valuable if it stays:

- debuggable
- bounded
- auditable
- contract-safe
- explainable enough to operate

The current repo already has strong instincts here. This phase generalizes them.

## Tool System

Create a shared tools layer under `learning_core/tools/` or `learning_core/runtime/tool_runtime.py`.

### Tool families to support initially

- `read_context`
- `read_pack_docs`
- `draft_artifact`
- `propose_adjustment`
- `synthesize_evidence`
- `create_recommendation`

These are generic learning-ops tool families, not homeschool-specific tools.

Actual domain tools may still live elsewhere, but the runtime should reason about them through these families.

### Tool rules

- tools must be explicitly allowed by task profile and workflow card
- tool calls must be logged consistently
- tool outputs should be previewed or summarized in traces
- tools should be typed and bounded
- no unrestricted database mutation tools

## Policy Layer

Create one shared policy model.

A policy object should help answer:

- Which tool families are allowed?
- Is multi-step looping allowed?
- What autonomy tier applies?
- Can the model propose durable changes?
- Can it auto-apply a change?
- Are pack-specific validators required?

### Core policy dimensions

- autonomy tier
- allowed tools
- maximum loop steps
- repair attempts
- pack restrictions
- artifact publication rules
- proposal vs applied behavior

## Validation

Validation needs two layers.

### Response-type validation

Every response type must validate its own schema.

### Task-specific validation

Some tasks need extra rules.

Examples:

- activity artifacts may require pack-specific widget validation
- lesson drafts may require block/time consistency checks
- proposals may require rationale and bounded change scope
- evaluation outputs may require evidence linkage fields

### Repair path

For recoverable failures, the runtime should support one bounded repair pass.

Typical repair inputs:

- validation error summary
- offending fields
- original task profile
- original response type

Do not create infinite repair loops.

## Retry Strategy

Build a shared retry policy with explicit failure classes.

Suggested failure classes:

- provider transient
- parsing failure
- contract mismatch
- loop exhaustion
- pack-validation failure
- tool precondition failure

Each class should map to an explicit retry or fail-fast behavior.

## Traces And Lineage

The runtime should produce one consistent trace shape regardless of task.

Minimum trace needs:

- operation name
- task profile
- requested response type
- runtime mode
- selected packs
- selected tools
- tool calls made
- retry/repair events
- validation steps
- provider metadata
- output lineage

This should preserve current useful observability while becoming more uniform.

## Preview Surface

Prompt preview or runtime preview should now include:

- task profile
- response type
- workflow card
- selected packs
- tools allowed
- system prompt
- user prompt
- runtime mode

This is important for agent development and debugging.

## First Migration Targets

As soon as these shared mechanisms exist, test them against:

- `activity_generate` because it has the richest bounded behavior already
- `session_generate` because it is central and simpler

## Out Of Scope

- event scheduler
- cross-product reporting layer
- store/app integration

## Success Criteria

Phase 4 is complete when:

- tool permissions are centrally controlled
- policy is explicit and reusable
- validation is shared and not buried in skill scripts
- retry behavior is consistent and inspectable
- traces are uniform enough to compare operations across the runtime
