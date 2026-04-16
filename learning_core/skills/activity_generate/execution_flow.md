# Activity Generate Execution Flow

This document maps the actual execution flow for `learning_core.skills.activity_generate`.

It is based on the implementation in:

- [scripts/main.py](/home/luke/Desktop/learning/learning-core/learning_core/skills/activity_generate/scripts/main.py)
- [scripts/tooling.py](/home/luke/Desktop/learning/learning-core/learning_core/skills/activity_generate/scripts/tooling.py)
- [validation/widgets.py](/home/luke/Desktop/learning/learning-core/learning_core/skills/activity_generate/validation/widgets.py)
- [packs/__init__.py](/home/luke/Desktop/learning/learning-core/learning_core/skills/activity_generate/packs/__init__.py)
- [packs/base.py](/home/luke/Desktop/learning/learning-core/learning_core/skills/activity_generate/packs/base.py)

## High-Level Flow

1. Parse the `ActivityGenerationInput`.
2. Select active packs using deterministic keyword matching.
3. Build the final user prompt from:
   - the lesson payload
   - the base UI registry
   - the pack index
   - active pack prompt docs
   - auto-injected widget specs for active packs
   - optional pack planning output
4. Expose tools:
   - always `read_ui_spec`
   - plus any tools owned by active packs
5. Run the agent loop.
6. Parse the model output into JSON.
7. Validate against the strict `ActivityArtifact` schema.
8. If schema validation fails, run a schema repair pass.
9. If pack widgets appear without required pack tool use, run a targeted pack-tool repair pass.
10. Run semantic validation:
    - base widget/runtime validation
    - pack-specific validation
11. If semantic hard errors exist, run a semantic repair pass.
12. Write provider logs and return:
    - validated artifact
    - lineage
    - trace

## Pack Retrieval Mechanism

There is no embedding retrieval, vector search, or fuzzy semantic lookup here.

Pack activation is currently deterministic `keyword matching`.

Implementation:
- `_select_packs(...)` in [scripts/main.py](/home/luke/Desktop/learning/learning-core/learning_core/skills/activity_generate/scripts/main.py)

Input fields considered:
- `payload.subject`
- `lesson.title`
- `lesson.lesson_focus`
- `" ".join(payload.linked_skill_titles)`

Each pack exposes:
- `name`
- `keywords`

Source of packs:
- `ALL_PACKS` in [packs/__init__.py](/home/luke/Desktop/learning/learning-core/learning_core/skills/activity_generate/packs/__init__.py)

Current packs:
- `ChessPack()`
- `MathPack()`
- `GeographyPack()`

### Matching Details

The helper `_contains_keyword(text, keyword)` does:

- lowercase normalization
- for multi-word keywords: plain substring match
- for single-word keywords: regex word-boundary-like match using:
  - `(?<![a-z])keyword(?![a-z])`

That means:
- `"map"` matches `"map study"`
- `"state boundaries"` matches as a substring
- the system is intentionally simple and deterministic

### What Gets Recorded

The system stores:
- `included_packs`
- `pack_selection_reason`
- `subject_inference`

These are included in provider logs and execution trace metadata.

## Prompt Construction

Implementation:
- `_build_user_prompt(...)` in [scripts/main.py](/home/luke/Desktop/learning/learning-core/learning_core/skills/activity_generate/scripts/main.py)

The final prompt is built as a single large text prompt with ordered sections.

### 1. Lesson-Derived Request Section

The prompt includes:
- learner name and grade
- subject
- session budget
- workflow mode
- lesson title
- lesson focus
- objectives
- success criteria
- lesson blocks
- materials
- teacher notes
- adaptations
- assessment artifact
- lesson shape
- linked objective IDs
- linked skill titles
- standard IDs
- user-authored context:
  - parent goal
  - author note
  - teacher note
  - special constraints
  - avoidances
  - custom instruction

This is the first major section of the user prompt.

### 2. Base UI Registry

The compressed base registry is appended from:
- [ui_registry_index.md](/home/luke/Desktop/learning/learning-core/learning_core/skills/activity_generate/ui_registry_index.md)

This gives the model:
- available top-level components
- available widget families
- usage guidance
- file paths for full UI docs

### 3. Pack Index

If any packs are active, the pack index is appended from:
- [packs/index.md](/home/luke/Desktop/learning/learning-core/learning_core/skills/activity_generate/packs/index.md)

This explains what each pack adds.

### 4. Active Pack Prompt Sections

For each active pack, `pack.prompt_sections()` is appended.

These sections typically come from pack-owned markdown like:
- `pack.md`
- `patterns.md`
- `examples.md`

So the mechanism is:
- deterministic pack selection
- then deterministic prompt inclusion of that pack’s markdown sections

It is not runtime retrieval from arbitrary docs.

### 5. Auto-Injected UI Specs

Packs may declare `auto_injected_ui_specs()`.

If they do, those UI docs are appended in full to the prompt automatically.

This is how active packs can include important widget specs without requiring the model to call `read_ui_spec`.

Example:
- geography auto-injects `ui_widgets/map_surface__geojson.md`

### 6. Optional Pack Planning Context

If a pack says it needs planning:
- `pack.needs_planning(...)`

then `pack.run_planning_phase(...)` runs before the final agent loop.

That planning output returns `PackPlanningResult`, which can include:
- `prompt_sections`
- `structured_data`

Those planning prompt sections are then appended as a `Pre-built pack planning context` section in the final prompt.

This lets a pack precompute validated examples before composition.

### 7. Final Generation Instruction

The prompt ends with strict generation instructions telling the model to:
- return a single `ActivitySpec` JSON object
- use `read_ui_spec` only when materially helpful
- use pack domain tools when required
- preserve validated examples when planning output exists
- emit no extra text outside JSON

## System Prompt

The system prompt is simply:
- [SKILL.md](/home/luke/Desktop/learning/learning-core/learning_core/skills/activity_generate/SKILL.md)

Loaded by `_read_skill_markdown()`.

## Tool Availability

Implementation:
- `_build_active_tools(...)` in [scripts/main.py](/home/luke/Desktop/learning/learning-core/learning_core/skills/activity_generate/scripts/main.py)

The tool set is:

- always:
  - `read_ui_spec`
- plus:
  - all tools returned by each active pack’s `tools()`

So tool access is also pack-gated.

If a pack is not active, its tools are not exposed.

## UI Spec Retrieval Mechanism

Implementation:
- `read_ui_spec(...)` in [scripts/tooling.py](/home/luke/Desktop/learning/learning-core/learning_core/skills/activity_generate/scripts/tooling.py)

This is not open-ended file access.

It is an `allowlisted file reader` over:
- `ui_components/*.md`
- `ui_widgets/*.md`

The allowlist lives in:
- `ALLOWED_UI_SPEC_PATHS`

Behavior:
- exact path match is preferred
- a single filename can resolve if it uniquely matches one allowlisted file
- invalid paths return an error string

So the retrieval model is:
- base registry gives short summaries and doc paths
- model may call `read_ui_spec(path)`
- only allowlisted UI docs can be read

## Agent Loop

Implementation:
- `run_agent_loop(...)` call in [scripts/main.py](/home/luke/Desktop/learning/learning-core/learning_core/skills/activity_generate/scripts/main.py)

The final generation run uses:
- the system prompt from `SKILL.md`
- the assembled user prompt
- active tools
- `max_steps=5`

The raw output is expected to be JSON, but the code still extracts JSON defensively.

## Schema Validation and First Repair

After generation:

1. Extract JSON text from the model output.
2. `json.loads(...)`
3. `ActivityArtifact.model_validate(...)`

If that fails:
- a repair prompt is sent back to the model
- the prompt includes:
  - validation error text
  - invalid JSON
  - instruction to make the smallest correction set

If repair fails again:
- execution raises `ContractValidationError`

## Pack Tool Usage Enforcement

Implementation:
- `_check_pack_tool_usage(...)` in [scripts/main.py](/home/luke/Desktop/learning/learning-core/learning_core/skills/activity_generate/scripts/main.py)

This step checks whether the artifact contains pack-specific widgets but the model never used that pack’s required tools.

Per pack:
- `detect_pack_widgets(artifact)` identifies relevant widgets
- `required_tool_names()` defines the required tool set

If a pack widget appears but none of the required tools were used:
- a targeted repair pass is triggered

The repair prompt includes:
- current JSON
- pack-specific repair guidance from `pack.repair_guidance()`
- instruction to validate the widget via domain tools and return corrected JSON

Important:
- this pass is best-effort
- failure here is logged
- execution continues into semantic validation anyway

## Semantic Validation

Implementation:
- `normalize_and_validate_widget_activity(...)` in [validation/widgets.py](/home/luke/Desktop/learning/learning-core/learning_core/skills/activity_generate/validation/widgets.py)

This stage does more than schema validation.

It checks:
- widget runtime semantics
- component composition semantics
- pack-specific validators

### Base Widget Validation

Examples:
- input widgets must have learner-facing instructions
- input widgets should not be `required: false`
- feedback/submission modes must be coherent
- captions should not duplicate prompts
- primary widgets should appear in sensible positions

This returns:
- `hard_errors`
- `soft_warnings`

Only `hard_errors` force repair.

### Pack Validators

Each active pack may contribute validators via:
- `pack.validators()`

Those validators can:
- normalize the artifact
- emit hard errors
- emit soft warnings

The pack validation context may include pack planning output through:
- `PackValidationContext(planning_result=...)`

## Semantic Repair Pass

If semantic hard errors exist:
- another repair prompt is built

That prompt includes:
- hard validation errors
- soft warnings
- current JSON
- optional validated planning context that must be preserved

Then the code:
1. asks the model to minimally fix the artifact
2. validates schema again
3. reruns semantic validation

If hard errors still remain:
- execution fails with `ContractValidationError`

Soft warnings after repair are acceptable.

## Logging and Trace

On success, the system writes:
- provider exchange log
- validated artifact
- tool call log
- UI specs read
- active tools
- repair flags
- pack selection metadata
- pack planning results
- pack validation results

The returned `ExecutionTrace.agent_trace` includes:
- `tool_calls`
- `ui_specs_read`
- `auto_injected_ui_specs`
- `active_tools`
- `included_packs`
- `pack_planning_results`
- `pack_selection_reason`
- `subject_inference`
- `repair_attempted`
- `repair_succeeded`
- `pack_tool_repair_triggered`
- `validation_error`
- `semantic_validation_hard_errors`
- `semantic_validation_soft_warnings`
- `pack_validation_results`

## End-to-End Summary

The retrieval and prompt-building model is:

1. Determine active packs using deterministic keyword matching.
2. Append pack docs into the prompt directly.
3. Auto-inject selected UI/widget docs for active packs.
4. Allow the model to read extra allowlisted UI docs through `read_ui_spec`.
5. Allow the model to use active pack tools only.
6. Enforce correctness afterward with:
   - schema validation
   - tool-usage repair
   - semantic validation
   - pack validators

So the pack access path is not opaque retrieval.

It is:
- deterministic activation by keywords
- deterministic inclusion of pack markdown sections
- optional targeted doc reads through an allowlisted tool
- optional pack-local planning
- post-generation repair and validation

