# matching_pairs

## Purpose
Learner matches items from a left column to corresponding items in a right column. Tests association knowledge.

## When to use
- Vocabulary-definition matching
- Concept-example pairing
- Cause-effect relationships
- Symbol-meaning associations

## When not to use
- More than 8 pairs — becomes overwhelming and tedious
- Items could match multiple things (ambiguous) — restructure the task
- One-to-many relationships — use categorization instead

## Fields

| Field | Type | Required | Default | Notes |
|-------|------|----------|---------|-------|
| id | string | yes | — | Unique kebab-case |
| type | `"matching_pairs"` | yes | — | |
| prompt | string or null | no | null | Instructions |
| pairs | array of pair objects | yes | — | Minimum 2 pairs |
| hint | string or null | no | null | Help text |

### Pair object

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| id | string | yes | Unique within this component |
| left | string | yes | Left-side item text |
| right | string | yes | Right-side item text |
| leftImageUrl | string or null | no | Optional image for left side |
| rightImageUrl | string or null | no | Optional image for right side |

## Example

```json
{
  "id": "match-vocab",
  "type": "matching_pairs",
  "prompt": "Match each vocabulary word with its definition:",
  "pairs": [
    { "id": "p1", "left": "Evaporation", "right": "Water turning from liquid to gas" },
    { "id": "p2", "left": "Condensation", "right": "Water vapor turning back into liquid" },
    { "id": "p3", "left": "Precipitation", "right": "Water falling from clouds as rain, snow, or hail" },
    { "id": "p4", "left": "Collection", "right": "Water gathering in bodies of water" }
  ],
  "hint": "Think about the water cycle stages in order."
}
```

## Evidence implications
- Produces `matching_result` evidence
- Auto-scorable: each pair is either correctly matched or not

## Scoring implications
- Use `correctness_based` scoring
- Set `autoScorable: true`
- Partial credit: fraction of correctly matched pairs

## Common mistakes
- Ambiguous pairs where multiple matches seem valid — each left must have exactly one clear right
- Too many pairs (>8) — UI becomes cramped and the task becomes tedious
- Using image URLs that don't exist — only include images when real URLs are available

## Pedagogy notes
Matching is effective for vocabulary, definitions, and association tasks. Keep pairs to 4-6 for younger learners, up to 8 for older. The right-side items are shuffled for the learner, so ensure each right-side text is distinct enough to avoid confusion.
