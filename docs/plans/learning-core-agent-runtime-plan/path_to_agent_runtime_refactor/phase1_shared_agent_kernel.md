# Phase 1: Shared Agent Kernel

## Objective

Extract one shared execution kernel that all major skills can eventually use.

This kernel should centralize the parts that are currently duplicated or inconsistently implemented across skills:

- request normalization
- context assembly hooks
- pack resolution hooks
- model runtime construction
- tool loop execution
- retries
- validation/finalization
- trace/lineage assembly
- prompt preview flow

The kernel should not erase task distinctions. It should provide a common execution backbone.

## Scope

Build a new internal runtime layer under `learning_core/runtime/` that can execute bounded tasks in a uniform way.

### Suggested Files

```text
learning_core/runtime/
  agent_kernel.py
  execution_loop.py
  request_normalization.py
  task_profiles.py
  pack_resolution.py
  tool_runtime.py
  validation.py
  finalization.py
  retries.py
  policy.py
  traces.py
  preview.py
```

## Kernel Responsibilities

### Request normalization

Convert the incoming operation envelope into a normalized runtime request:

- operation name
- task profile
- requested response type
- workflow mode
- template
- surface
- actor role
- autonomy tier
- latency class
- pack hints
- tool policy
- context bundle
- raw input payload

This runtime request becomes the common input to the rest of the kernel.

### Execution loop

The loop should support two modes:

1. **single-pass bounded generation**
   - for simple tasks with no tool use or minimal tool use
2. **agentic bounded loop**
   - for tasks where the model may need to read pack docs, inspect specs, or call domain tools before finalizing

Do not force all tasks into a multi-step loop.

### Tool runtime

Tools must be registered and invoked through a shared interface.

The runtime should:

- resolve allowed tools for the task
- expose them to the model loop if permitted
- log tool calls consistently
- keep tool use bounded and auditable

### Validation and finalization

Validation must be a formal step, not an afterthought.

The finalizer should:

- parse output
- validate against the requested response type contract
- run task-specific final validators if needed
- return typed artifact + traces + lineage

### Retry behavior

Retry logic should be shared and policy-aware.

Different failure modes should produce different strategies:

- parsing failure
- contract validation failure
- provider transient failure
- recursion/step exhaustion
- missing tool result

Do not bury retry logic inside individual skills.

### Prompt preview

Prompt preview should continue to work even after the refactor.

The preview path should show:

- resolved system prompt
- resolved user prompt
- task profile
- active packs
- active tools
- runtime mode

## AgentKernel Interface

A clean interface could look like:

```python
class AgentKernel:
    def preview(self, runtime_request: RuntimeRequest) -> KernelPreview: ...
    def execute(self, runtime_request: RuntimeRequest) -> KernelExecutionResult: ...
```

Where `RuntimeRequest` is already normalized and the rest of the kernel is hidden behind that boundary.

## Runtime Request Example

```python
RuntimeRequest(
    operation_name="session_generate",
    task_profile="bounded_day_generation",
    requested_response_type="lesson_draft",
    template="homeschool",
    workflow_mode="family_guided",
    surface="onboarding",
    actor_role="adult",
    autonomy_tier="draft",
    latency_class="interactive",
    context_bundle={...},
    raw_payload={...},
    pack_hints=["homeschool", "reading"],
)
```

## Migration Strategy For This Phase

Do not migrate all operations at once.

Start by implementing the kernel and routing just one or two operations through it in shadow mode or behind feature flags.

Best first candidates:

- `session_generate`
- `activity_generate`

Why:

- both are central to the product experience
- one is simpler and common (`session_generate`)
- one already has the strongest bounded-agent structure (`activity_generate`)

## Required Decisions

- Which parts of current operation execution are duplicated today?
- Which execution results are shared enough to centralize now?
- Which task-specific pieces must remain outside the kernel?
- How much of prompt construction belongs in the kernel versus workflow cards?

## Out Of Scope

- generic public API changes
- pack redesign across all skills
- new response contracts
- new product flows

## Success Criteria

Phase 1 is complete when:

- there is one internal execution kernel
- it can preview and execute at least one migrated task
- the migrated task still returns the same contract shape as before
- tool logging, traces, and validation are at least as good as before
- task-specific prompt instructions remain task-specific rather than collapsing into a giant shared prompt
