# Skill Assumption Audit

Date: 2026-04-20
Repo: `learning-core`
Scope: `learning_core/skills/**` with non-Copilot fixes only, plus narrowly related tests.

## Audit baseline

This audit used the current intended architecture as the source of truth:

- homeschool-first app domain
- current wedge: bring what you already have -> create a usable curriculum / launch window -> open today fast -> keep the week and records nearby
- canonical generation chain: `source_interpret -> curriculum_generate -> planning/progression/day 1`
- `learning-core` is the strict AI/runtime boundary
- Copilot actions must be bounded app-side approvals
- billing is deferred and out of scope

## Summary

Read every skill directory under `learning_core/skills/*`, including `copilot_chat` for classification only. Patched only the clearly stale or under-specified non-Copilot skills:

- `curriculum_intake`
- `progression_revise`
- `session_evaluate`
- `launch_plan_generate`
- `tests/test_source_interpret.py` to remove a stale `launchPlan` expectation

No non-Copilot contracts required code changes in this pass.

## Skill-by-skill classification

| Skill | Classification | Notes | Action |
|---|---|---|---|
| `source_interpret` | aligned | Uses the current source taxonomy, bounded horizon model, and interpretation-only role. Does not overstep into curriculum or lesson generation. | no change |
| `curriculum_generate` | aligned but intentionally homeschool-specific | Correctly owns durable curriculum creation, treats `source_entry` as the canonical source-first path, and explicitly excludes `launchPlan`, lessons, and progression from its artifact. Homeschool tone is deliberate for current product stage. | no change |
| `curriculum_intake` | assumption mismatch | Prompt still said the conversation should gather enough to build a "lesson sequence", which conflicts with the current architecture where intake feeds durable curriculum generation and later progression/day-1 planning. | patched |
| `curriculum_revise` | aligned but intentionally homeschool-specific | Revises the durable curriculum artifact only and preserves the canonical tree shape. Homeschool framing is acceptable at the current launch stage. | no change |
| `curriculum_update_propose` | unclear / under-specified | Only a short `SKILL.md` exists. No runtime registration, script, or active product path was found in this pass. It reads like deferred design residue rather than a current operational skill. | deferred, documented only |
| `launch_plan_generate` | architecture mismatch | Still exists as a registered operation even though the current canonical chain is `source_interpret -> curriculum_generate -> progression/day 1`. The opening-window concept is real, but this standalone skill is no longer the clearest current source of truth. | prompt reframed as optional opening-window selector; broader cleanup deferred |
| `progression_generate` | aligned | Matches the current architecture well: canonical skill refs, authored unit order, bounded sequencing rules, and explicit separation from curriculum generation and lesson planning. | no change |
| `progression_revise` | assumption mismatch | Revision prompt was much looser than `progression_generate` and did not enforce exact `skillRef` copying, unit-anchor grounding, or phase-description quality. That was risky for the current strict progression contract. | patched |
| `session_generate` | aligned but intentionally homeschool-specific | Bounded day generation for a parent-facing teaching interface fits the current product. Parent/non-expert teacher assumptions are acceptable for closed beta. | no change |
| `session_evaluate` | unclear / under-specified | `SKILL.md` was still a legacy-placeholder note instead of a real evaluator prompt, which left the current rating semantics and evidence expectations underspecified. | patched |
| `activity_generate` | aligned but intentionally homeschool-specific | Properly treats activities as bounded, lesson-grounded artifacts rendered by a constrained component library. Parent/teacher support language and homeschool tone are intentional and acceptable now. | no change |
| `activity_feedback` | aligned | Operates as a bounded learner-response evaluation path and does not try to redesign activities or mutate curriculum state. | no change |
| `widget_transition` | aligned | Deterministic bounded runtime transition path. Matches the strict backend-owned widget state model. | no change |
| `copilot_chat` | architecture mismatch | Read for classification only. Current implementation is still answer-only and lacks the bounded action contract required by the target architecture. Another worker owns the fix. | deferred to Copilot worker |

## Mismatches fixed now

### `curriculum_intake`

- Removed the stale implication that intake should gather enough to build a lesson sequence.
- Reframed intake as gathering enough signal for a durable curriculum artifact plus later progression/day-1 handoff.

### `progression_revise`

- Tightened the system prompt to match the current strict progression model.
- Added exact `skillRef` copy rules so revisions cannot reconstruct or paraphrase refs.
- Added unit-anchor grounding and current source metadata to the revision prompt.
- Added explicit phase-description and ordering guardrails to reduce invalid or weak revision artifacts.

### `session_evaluate`

- Replaced the legacy-placeholder `SKILL.md` with a real evaluation prompt.
- Made the rating semantics explicit in the prompt itself.
- Added evidence-grounding and conservative-judgment rules.
- Clarified that `nextActions` are short follow-up teaching moves, not curriculum rewrites.

### `launch_plan_generate`

- Reframed the skill as an optional opening-window selector rather than part of the canonical curriculum-creation chain.
- Clarified that it does not own durable curriculum state.
- Left the operation in place for compatibility because removing runtime registration was outside this slice.

### stale orchestration test

- Updated `tests/test_source_interpret.py` to stop expecting `curriculum_generate` to return `launchPlan`.
- The test now asserts that `launchPlan` is absent from the curriculum artifact and that `recommendedHorizon` survives in the orchestration trace from `source_interpret`.

## Intentionally left homeschool-specific

These skills still speak directly to homeschooling, parents, or home-teaching execution. That is acceptable for the current launch stage and not treated as drift:

- `curriculum_generate`
- `curriculum_intake`
- `curriculum_revise`
- `session_generate`
- `session_evaluate`
- `activity_generate`

## Deferred items

### `copilot_chat`

- Out of write scope for this worker.
- Current answer-only behavior conflicts with the target bounded-action model.
- Another worker should handle the contract, prompt, runtime shape, and app integration.

### `launch_plan_generate` runtime presence

- Prompt is now framed more honestly, but the standalone operation still exists in runtime registration, API listings, and tests.
- If the product truly no longer wants a separate launch-plan operation, that wider removal should happen in a coordinated follow-up because it touches registry, docs, tests, and possibly app callers.

### `curriculum_update_propose`

- Still looks like deferred scaffolding rather than an active operational skill.
- Needs a product decision: either implement it with a real contract/runtime path or remove it from docs and planning artifacts.

### docs drift outside this write scope

These were observed during the skill audit and should be handled by the docs worker:

- `docs/source-taxonomy-model.md` still says `curriculum_generate` returns a durable curriculum artifact with `launchPlan`, which conflicts with the current contract and `SKILL.md`.
- `README.md` still references `launch_plan_generate` as a first-class current flow.

## Files changed in this pass

- `learning_core/skills/curriculum_intake/SKILL.md`
- `learning_core/skills/curriculum_intake/scripts/main.py`
- `learning_core/skills/progression_revise/SKILL.md`
- `learning_core/skills/progression_revise/scripts/main.py`
- `learning_core/skills/session_evaluate/SKILL.md`
- `learning_core/skills/session_evaluate/scripts/main.py`
- `learning_core/skills/launch_plan_generate/SKILL.md`
- `learning_core/skills/launch_plan_generate/scripts/main.py`
- `tests/test_source_interpret.py`

## Verification plan used

- read every skill directory under `learning_core/skills/*`
- compared prompts and request/response contracts against current runtime contracts
- checked runtime orchestration in `learning_core/runtime/engine.py`
- checked registry/task-profile presence for potentially stale operations
- patched the stale `launchPlan` orchestration expectation in tests

## Verification results

- `python3 -m py_compile` passed for the touched Python files and the patched test file.
- Targeted `pytest` collection could not complete in this shell because the local environment is missing repo dependencies such as `langchain_core` and `chess`.
- Bare `pytest` also auto-loaded a broken external plugin (`pytest_vcr`) until plugin autoload was disabled.
