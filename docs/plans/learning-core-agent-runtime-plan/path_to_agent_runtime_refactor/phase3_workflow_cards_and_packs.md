# Phase 3: Workflow Cards And Packs

## Objective

Replace ad hoc skill-specific prompt composition with a more uniform structure built from:

- workflow cards
- pack resolution

This is the phase that gives the runtime a consistent internal language without making it homeschool-specific.

## Conceptual Model

### Workflow cards

A workflow card is a bounded job recipe.

It defines:

- what the task is trying to produce
- what context matters most
- which tools are allowed
- what output contract is expected
- what guardrails apply
- how the user prompt should be composed

Workflow cards are not UI screens. They are execution recipes.

### Packs

A pack is reusable domain or interaction context that can be layered into a task.

Packs should be composable and optional.

Examples:

- domain packs: homeschool, tutoring, workforce
- subject packs: math, chess, reading, writing, science
- interaction packs: widgets, assessment styles, evidence patterns

## Why This Phase Matters

Right now, `activity_generate` already points in this direction with subject packs and strong bounded policy. That is the best current pattern to generalize.

The goal is to make other capabilities benefit from the same structure without flattening them into one universal skill.

## Suggested Layout

```text
learning_core/
  workflow_cards/
    onboarding_intake/
      card.py
      prompt.md
      policy.py
    bounded_day_generation/
      card.py
      prompt.md
      policy.py
    weekly_expansion/
      card.py
      prompt.md
      policy.py
    session_synthesis/
      card.py
      prompt.md
      policy.py
    reporting/
      card.py
      prompt.md
      policy.py
  packs/
    domains/
      homeschool/
      tutoring/
      workforce/
    subjects/
      math/
      chess/
      reading/
      writing/
      science/
    interactions/
      widgets/
      assessment_styles/
      evidence_patterns/
```

## Workflow Card Rules

Every workflow card should declare:

- supported task profiles
- supported response types
- base system prompt or instructions
- context assembly requirements
- allowed tool families
- pack categories it can consume
- finalization rules
- validation extensions

### Candidate cards for first migration

- `bounded_day_generation`
- `session_synthesis`
- `reporting`

And later:

- `onboarding_intake`
- `weekly_expansion`

## Pack Rules

Each pack should contribute only bounded things:

- vocabulary
- heuristics
- examples
- constraints
- optional tool registrations
- optional validation extensions
- optional UI/widget docs for interactive tasks

Packs should not become mini-products.

### Domain packs

Domain packs are where market-specific tuning belongs.

Examples:

- homeschool
- tutoring
- workforce
- certification prep

This is the correct place for homeschool-specific assumptions, not the kernel.

### Subject packs

Subject packs should stay as small, reusable knowledge and interaction layers.

Examples:

- chess
- math
- reading
- science

### Interaction packs

Interaction packs should capture things like:

- assessment styles
- evidence collection patterns
- supported widget conventions
- reflection or feedback patterns

## Pack Resolution

The runtime should resolve packs from a combination of:

- explicit pack hints from the request
- workflow card defaults
- subject signals from the payload
- template/workflow mode
- guardrail policy

Pack resolution should be explainable and visible in traces.

## Key Design Boundary

Do not make workflow cards or packs depend on `homeschool-v2` route names or UI assumptions.

The app may say:

- `template = homeschool`
- `surface = onboarding`
- `workflow_mode = family_guided`

But the card/pack system should stay reusable for other products.

## First Concrete Refactor Target

Take the strong ideas already in `activity_generate` and extract them into reusable concepts:

- active packs
- pack-selected tools
- pack-specific prompt sections
- pack validation hooks
- pack planning phases when needed

Then apply that model to at least one non-activity capability, ideally `session_generate`.

## Out Of Scope

- final generic endpoint rollout
- broad app integration changes
- full pack library for all future markets

## Success Criteria

Phase 3 is complete when:

- workflow cards exist as first-class runtime units
- packs exist outside individual skills as reusable modules or at least a clearly shared layer
- `session_generate` or another non-activity task can consume the same pack/card architecture
- homeschool-specific tuning exists as a pack or template layer rather than in the kernel itself
