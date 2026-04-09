# drag_arrange

## Purpose
Learner arranges items by dragging them into a desired spatial order. Unlike ordered_sequence, there is no single correct order defined — the arrangement itself is the response.

## When to use
- Free-form prioritization or ranking
- Spatial arrangement where the learner's chosen order is the evidence
- Timeline construction from a learner's perspective
- "Arrange these in order of importance to you"

## When not to use
- There is one correct order — use ordered_sequence instead
- Grouping into categories — use categorization or sort_into_groups
- Only 2 items — too trivial for drag interaction

## Fields

| Field | Type | Required | Default | Notes |
|-------|------|----------|---------|-------|
| id | string | yes | — | Unique kebab-case |
| type | `"drag_arrange"` | yes | — | |
| prompt | string | yes | — | Instructions for the arrangement |
| items | array of item objects | yes | — | Minimum 2 items |
| hint | string or null | no | null | Help text |

### Item object

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| id | string | yes | Unique within this component |
| text | string | yes | Display text for the item |

## Example

```json
{
  "id": "arrange-priorities",
  "type": "drag_arrange",
  "prompt": "Arrange these study strategies from most helpful to least helpful for you:",
  "items": [
    { "id": "flash", "text": "Flashcards" },
    { "id": "notes", "text": "Taking notes" },
    { "id": "teach", "text": "Teaching someone else" },
    { "id": "practice", "text": "Practice problems" }
  ],
  "hint": "Think about which strategies have worked best for you in the past."
}
```

## Evidence implications
- Produces `ordering_result` evidence
- The final arrangement order is captured — no "correct" answer is defined
- Useful for understanding learner preferences and metacognition

## Scoring implications
- Typically `completion_based` (no correct order)
- Not auto-scorable
- Set `autoScorable: false`

## Common mistakes
- Confusing with ordered_sequence — drag_arrange has no `correctIndex`, ordered_sequence does
- Using for objectively ordered content (that's ordered_sequence)

## Pedagogy notes
Drag arrange captures the learner's own reasoning about priority, preference, or importance. It's a good metacognitive tool — "how do you think about this?" rather than "what's the right answer?" Pair with a text_response asking the learner to explain their arrangement.
