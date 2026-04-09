# ordered_sequence

## Purpose
Learner arranges items into the correct order. Tests understanding of sequences, processes, timelines, or procedures.

## When to use
- Ordering steps of a process (e.g., scientific method, long division steps)
- Chronological sequencing (historical events, story plot points)
- Ranking by a specific criterion (smallest to largest, etc.)

## When not to use
- Order doesn't matter — use checklist
- Spatial arrangement matters — use drag_arrange
- Grouping/classification — use categorization or sort_into_groups

## Fields

| Field | Type | Required | Default | Notes |
|-------|------|----------|---------|-------|
| id | string | yes | — | Unique kebab-case |
| type | `"ordered_sequence"` | yes | — | |
| prompt | string | yes | — | Instructions for what to order |
| items | array of item objects | yes | — | Minimum 2 items; presented scrambled |
| hint | string or null | no | null | Help text |

### Item object

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| id | string | yes | Unique within this component |
| text | string | yes | Display text for the item |
| correctIndex | integer | yes | 0-based correct position |

## Example

```json
{
  "id": "seq-division",
  "type": "ordered_sequence",
  "prompt": "Put the long division steps in the correct order:",
  "items": [
    { "id": "s-divide", "text": "Divide", "correctIndex": 0 },
    { "id": "s-multiply", "text": "Multiply", "correctIndex": 1 },
    { "id": "s-subtract", "text": "Subtract", "correctIndex": 2 },
    { "id": "s-bring-down", "text": "Bring down", "correctIndex": 3 }
  ],
  "hint": "Remember the D-M-S-B pattern."
}
```

## Evidence implications
- Produces `ordering_result` evidence
- Auto-scorable: compare learner's order to correctIndex values

## Scoring implications
- Use `correctness_based` scoring
- Set `autoScorable: true`
- Partial credit is possible (how many items in correct position)

## Common mistakes
- `correctIndex` values not forming a contiguous 0-based sequence (0, 1, 2, ...)
- Too many items (>8) — becomes a memory task rather than understanding
- Using for ranking preferences (subjective) — ordered_sequence implies a single correct order

## Pedagogy notes
Sequencing tasks test procedural knowledge — does the learner understand the process, not just the facts? Keep to 4-6 items for most age groups. Include the hint to scaffold first attempts. Items are shown scrambled, so make each item text clear enough to stand alone.
