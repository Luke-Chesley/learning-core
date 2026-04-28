# Source Taxonomy Model

This note captures the `learning-core` side of the taxonomy refactor used by `source_interpret` and `curriculum_generate`.

## Source Interpret Contract

`source_interpret` now returns:

- `sourceKind`
- `entryStrategy`
- `entryLabel`
- `continuationMode`
- `recommendedHorizon`
- `planningConstraints`

The canonical `sourceKind` values are:

- `bounded_material`
- `timeboxed_plan`
- `structured_sequence`
- `comprehensive_source`
- `curriculum_request`
- `topic_seed`
- `shell_request`
- `ambiguous`

`comprehensive_source` is the bucket for whole books, workbooks, long PDFs, teacher guides, and other sources that clearly exceed a short start. The contract must still choose a bounded opening slice instead of treating the full source as immediate plan scope.

`curriculum_request` is the bucket for parent-authored requests to design a curriculum/module/course from a topic and constraints. The interpreter must not generate the curriculum, but it must extract explicit scope into `planningConstraints`.

`topic_seed` is now reserved for loose topic exploration without an explicit curriculum/module/course request or pacing constraint.

`planningConstraints` carries fields such as `totalSessions`, `totalWeeks`, `sessionsPerWeek`, `sessionMinutes`, `gradeLevel`, `learnerContext`, `practiceCadence`, and `finalProjectRequested`.

## recommendedHorizon

`recommendedHorizon` describes the safest initial planning window:

- `single_day`
- `few_days`
- `one_week`
- `two_weeks`
- `starter_module`

It is a launch recommendation, not a promise about total curriculum size.

## curriculum_generate

`curriculum_generate` is the only curriculum-creation skill.

- `requestMode: "source_entry"` is used for source-first flows after `source_interpret`
- `requestMode: "conversation_intake"` is used for regular curriculum creation without source interpretation

Both modes return one durable curriculum artifact.

- For `comprehensive_source`, the curriculum should reflect the broader source in teachable order.
- The artifact must include a concrete teachable content map: `contentAnchors`, `teachableItems`, and content-grounded `skills`.
- `planningModel` communicates whether the artifact is a flexible content map, authored source sequence, reference map, single lesson, or explicit session sequence.
- For `timeboxed_plan`, `planningModel` should be `session_sequence`, and `deliverySequence` should contain one concrete item per requested session.
- For `curriculum_request` with `planningConstraints.totalSessions`, `planningModel` should be `session_sequence`, `pacing.totalSessions` should preserve that number, and `deliverySequence` should contain one concrete item per session.
- Opening-window and day-1 handoff are downstream concerns for app planning flow or separate bounded operations.
- Weak inputs should stay small; strong sources should not collapse into a shallow launch week.

Older docs that say every `curriculum_generate` response includes `launchPlan` are stale.

## No User Horizon Choice

The contract no longer accepts a user-controlled horizon preference. The interpreter owns the bounded launch recommendation and downstream callers may clamp or confirm it, but they should not present it as an arbitrary user picker.

## Continuation Metadata

`continuationMode` is the lightweight signal for future continuation:

- `none`
- `sequential`
- `timebox`
- `manual_review`

This does not implement continuation itself. It only tells later orchestration how the next bounded slice should probably continue.
