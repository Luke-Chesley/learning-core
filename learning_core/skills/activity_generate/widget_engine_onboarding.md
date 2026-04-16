# Widget Engine Onboarding

This document explains how to add a new engine-backed widget or subject pack without hard-coding a one-off flow.

It complements [execution_flow.md](/home/luke/Desktop/learning/learning-core/learning_core/skills/activity_generate/execution_flow.md), which explains how `activity_generate` builds prompts and activates packs.

## Design Goal

The system is intentionally split into:

- a shared shell
- engine-specific adapters

The shared shell should stay stable as new packs arrive. New packs should plug into a predictable set of extension points instead of rewriting the full runtime.

## Shared Shell

These layers are generic across engines:

- `interactive_widget` in [`learning_core/contracts/activity.py`](/home/luke/Desktop/learning/learning-core/learning_core/contracts/activity.py)
- widget payload union in [`learning_core/contracts/widgets.py`](/home/luke/Desktop/learning/learning-core/learning_core/contracts/widgets.py)
- widget transition request/response envelope in [`learning_core/contracts/widget_transition.py`](/home/luke/Desktop/learning/learning-core/learning_core/contracts/widget_transition.py)
- feedback envelope in [`learning_core/contracts/activity_feedback.py`](/home/luke/Desktop/learning/learning-core/learning_core/contracts/activity_feedback.py)
- prompt assembly and pack injection in [`learning_core/skills/activity_generate/scripts/main.py`](/home/luke/Desktop/learning/learning-core/learning_core/skills/activity_generate/scripts/main.py)
- local debug renderer shell in [`local_test/static/app.js`](/home/luke/Desktop/learning/learning-core/local_test/static/app.js)

This means a new engine does not need a new top-level operation or a custom app path. It needs a new adapter behind the existing operations.

## Runtime Model

Today the runtime is generic at the envelope level and explicit at the engine level.

That is the intended model.

- `activity_generate` authors the widget payload.
- `widget_transition` applies learner actions to canonical widget state.
- `activity_feedback` evaluates the learner response.
- `local_test` renders the widget for debug.

The extension point is the engine adapter, not a new end-to-end pipeline.

## Required Pieces For A New Engine

### 1. Widget contract

Add the widget payload to [`learning_core/contracts/widgets.py`](/home/luke/Desktop/learning/learning-core/learning_core/contracts/widgets.py).

The contract should define:

- `surfaceKind`
- `engineKind`
- `version`
- `surface`
- `display`
- `state`
- `interaction`
- `feedback`
- `evaluation`
- `annotations`

Keep the payload bounded. Do not use freeform catch-all fields.

### 2. Activity generation docs

Add or update:

- `ui_widgets/<surface>__<engine>.md`
- pack docs under `packs/<pack>/`

These docs are what the model sees during prompt assembly. If the widget docs are vague, generation quality will be vague too.

### 3. Pack validation

If the engine belongs to a pack, add validation in the pack toolchain.

Typical places:

- pack validators in `packs/<pack>/validation.py`
- pack tools in `packs/<pack>/tools.py`

The goal is to reject malformed engine payloads before they reach runtime.

### 4. Widget transition adapter

Add the learner action types to [`learning_core/contracts/widget_transition.py`](/home/luke/Desktop/learning/learning-core/learning_core/contracts/widget_transition.py).

Then add an engine handler in [`learning_core/skills/widget_transition/scripts/main.py`](/home/luke/Desktop/learning/learning-core/learning_core/skills/widget_transition/scripts/main.py).

Recommended pattern:

- keep shared actions when possible, such as `reset` and `set_text_value`
- add engine-specific actions only when the interaction truly needs them
- register the handler by `engineKind`

Current examples:

- `chess` uses `select_square` and `submit_move`
- `map_geojson` uses `select_feature`, `place_marker`, and other map actions
- `math_symbolic` reuses `set_text_value`
- `graphing` currently reuses `set_text_value`

### 5. Deterministic feedback adapter

Add deterministic evaluation in [`learning_core/skills/activity_feedback/scripts/main.py`](/home/luke/Desktop/learning/learning-core/learning_core/skills/activity_feedback/scripts/main.py).

Prefer deterministic evaluation whenever the engine has a bounded target.

Examples:

- `chess`: exact move matching
- `map_geojson`: feature, marker, path, and label checks
- `math_symbolic`: expected expression comparison
- `graphing`: lightweight expected graph description comparison

If deterministic evaluation is not yet possible, return `needs_review` cleanly instead of silently falling into a low-quality path.

### 6. Local debug renderer

Add a renderer adapter in [`local_test/static/app.js`](/home/luke/Desktop/learning/learning-core/local_test/static/app.js).

The renderer should:

- display the widget state clearly
- send learner actions through `widget_transition`
- send submissions through `activity_feedback`
- show the returned feedback inline

This renderer is for debug quality, not visual polish.

### 7. Smoke coverage

Add a case to [`local_test/smoke_cases.json`](/home/luke/Desktop/learning/learning-core/local_test/smoke_cases.json) and exercise it in [`local_test/smoke_harness_runner.js`](/home/luke/Desktop/learning/learning-core/local_test/smoke_harness_runner.js).

Every engine should have at least one local path that proves:

- generation returns a valid widget
- the local renderer can display it
- at least one transition works
- feedback returns a valid artifact

## What Should Be Shared vs Explicit

### Share these

- request envelopes
- response envelopes
- tracing
- render shell
- retry/reset semantics
- simple action types like `reset`

### Keep these explicit per engine

- state mutation logic
- legal action checks
- deterministic evaluation logic
- engine-specific visual rendering

Trying to make all engine behavior fully generic usually collapses into vague contracts and brittle runtime code.

The correct balance is:

- generic shell
- explicit adapters

## Existing Engines As Examples

### Chess

Files:

- [`learning_core/contracts/widgets.py`](/home/luke/Desktop/learning/learning-core/learning_core/contracts/widgets.py)
- [`learning_core/contracts/widget_transition.py`](/home/luke/Desktop/learning/learning-core/learning_core/contracts/widget_transition.py)
- [`learning_core/skills/widget_transition/scripts/main.py`](/home/luke/Desktop/learning/learning-core/learning_core/skills/widget_transition/scripts/main.py)
- [`learning_core/skills/activity_feedback/scripts/main.py`](/home/luke/Desktop/learning/learning-core/learning_core/skills/activity_feedback/scripts/main.py)

Pattern:

- board widget
- square selection
- move submission
- deterministic move evaluation

### Geography

Files:

- [`learning_core/skills/activity_generate/packs/geography/`](/home/luke/Desktop/learning/learning-core/learning_core/skills/activity_generate/packs/geography)
- [`learning_core/skills/activity_generate/ui_widgets/map_surface__geojson.md`](/home/luke/Desktop/learning/learning-core/learning_core/skills/activity_generate/ui_widgets/map_surface__geojson.md)

Pattern:

- source-backed widget
- geometry-backed transition checks
- deterministic map evaluation

### Math Symbolic

Pattern:

- bounded symbolic entry widget
- `set_text_value` transition
- exact or normalized expression comparison

### Graphing

Pattern:

- graph widget with bounded state
- `set_text_value` transition for the current local renderer
- deterministic description match for the current debug path

This is intentionally modest. It gives the engine a stable shell now and leaves room for richer graph-native actions later.

## Recommended Onboarding Checklist

When adding a new pack or engine, verify all of these before calling it done:

1. The widget contract exists and validates.
2. The generation docs match the contract exactly.
3. The pack validator rejects malformed engine payloads.
4. `widget_transition` accepts at least one real learner action.
5. `activity_feedback` returns a valid artifact for that engine.
6. `local_test` can render and exercise the engine.
7. A smoke case proves the whole loop.

## Common Failure Modes

- Widget docs drift from the actual Pydantic contract.
- The model invents engine ids, source ids, or evaluation fields.
- `widget_transition` supports rendering but not canonical state changes.
- `activity_feedback` forgets to extract the engine's expected answer field.
- The local renderer displays the widget but never calls the runtime operations.

When debugging, check the flow in this order:

1. contract
2. generation docs
3. pack validation
4. transition adapter
5. feedback adapter
6. local renderer

