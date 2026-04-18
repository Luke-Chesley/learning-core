# Source Taxonomy Model

This note captures the `learning-core` side of the taxonomy refactor used by `source_interpret` and `bounded_plan_generate`.

## Source Interpret Contract

`source_interpret` now returns:

- `sourceKind`
- `entryStrategy`
- `entryLabel`
- `continuationMode`
- `recommendedHorizon`

The canonical `sourceKind` values are:

- `bounded_material`
- `timeboxed_plan`
- `structured_sequence`
- `comprehensive_source`
- `topic_seed`
- `shell_request`
- `ambiguous`

`comprehensive_source` is the bucket for whole books, workbooks, long PDFs, teacher guides, and other sources that clearly exceed a short start. The contract must still choose a bounded opening slice instead of treating the full source as immediate plan scope.

## recommendedHorizon

`recommendedHorizon` describes the safest initial planning window:

- `single_day`
- `few_days`
- `one_week`
- `two_weeks`
- `starter_module`

It is a launch recommendation, not a promise about total curriculum size.

## No User Horizon Choice

The contract no longer accepts a user-controlled horizon preference. The interpreter owns the bounded launch recommendation and downstream callers may clamp or confirm it, but they should not present it as an arbitrary user picker.

## Continuation Metadata

`continuationMode` is the lightweight signal for future continuation:

- `none`
- `sequential`
- `timebox`
- `manual_review`

This does not implement continuation itself. It only tells later orchestration how the next bounded slice should probably continue.
