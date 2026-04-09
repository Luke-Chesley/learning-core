# choose_next_step

## Purpose
Learner selects their preferred next action from a set of choices. Gives the learner agency in directing their learning path.

## When to use
- Branching activities where learner choice affects the path
- "What would you like to explore next?"
- Differentiation: learner self-selects difficulty or topic
- End-of-activity choices for extension

## When not to use
- Only one valid path — no real choice to make
- Testing knowledge (right/wrong) — use single_select
- The choice has no meaningful consequence

## Fields

| Field | Type | Required | Default | Notes |
|-------|------|----------|---------|-------|
| id | string | yes | — | Unique kebab-case |
| type | `"choose_next_step"` | yes | — | |
| prompt | string | yes | — | What to decide |
| choices | array of choice objects | yes | — | Minimum 2 choices |

### Choice object

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| id | string | yes | Unique within this component |
| label | string | yes | Short choice label |
| description | string or null | no | What this choice leads to or involves |

## Example

```json
{
  "id": "choose-extension",
  "type": "choose_next_step",
  "prompt": "Great work! What would you like to do next?",
  "choices": [
    { "id": "harder", "label": "Try a harder problem", "description": "A challenge problem with larger numbers" },
    { "id": "review", "label": "Review what I learned", "description": "Go back over the key steps" },
    { "id": "done", "label": "I'm finished for today", "description": "Mark this session as complete" }
  ]
}
```

## Evidence implications
- Produces `completion_marker` evidence
- The choice itself is captured — reveals learner self-assessment and motivation

## Scoring implications
- Typically `completion_based`
- Not auto-scorable (no correct answer)

## Common mistakes
- Choices that don't represent meaningfully different options
- Missing descriptions — labels alone may not give enough context

## Pedagogy notes
Learner agency improves engagement and self-regulation. Choose-next-step is especially valuable at the end of an activity as a natural transition point. The learner's choice gives the teacher signal about confidence and motivation.
