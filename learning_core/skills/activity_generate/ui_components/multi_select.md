# multi_select

## Purpose
Checkbox-style selection where the learner picks one or more correct answers from a set of options.

## When to use
- Multiple correct answers exist (e.g., "Select all that apply")
- Testing ability to distinguish correct from incorrect across a set
- Classification tasks where items may belong to multiple categories

## When not to use
- Only one correct answer — use single_select
- Subjective preference — use rating or checklist
- Ordering matters — use ordered_sequence

## Fields

| Field | Type | Required | Default | Notes |
|-------|------|----------|---------|-------|
| id | string | yes | — | Unique kebab-case |
| type | `"multi_select"` | yes | — | |
| prompt | string | yes | — | The question |
| choices | array of choice objects | yes | — | Minimum 2 choices |
| minSelections | integer or null | no | null | Minimum selections required (>= 0) |
| maxSelections | integer or null | no | null | Maximum selections allowed (> 0) |
| hint | string or null | no | null | Help text |
| required | boolean | no | true | |

### Choice object

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| id | string | yes | Unique within this component |
| text | string | yes | Display text |
| correct | boolean or null | no | Mark correct choices |

## Example

```json
{
  "id": "q-renewable",
  "type": "multi_select",
  "prompt": "Select all renewable energy sources:",
  "choices": [
    { "id": "a", "text": "Solar power", "correct": true },
    { "id": "b", "text": "Coal", "correct": false },
    { "id": "c", "text": "Wind power", "correct": true },
    { "id": "d", "text": "Natural gas", "correct": false },
    { "id": "e", "text": "Hydroelectric", "correct": true }
  ],
  "hint": "Think about which sources can be replenished naturally.",
  "required": true
}
```

## Evidence implications
- Produces `answer_response` evidence
- With `correct` markings, enables auto-scoring (all correct + no incorrect = full marks)

## Scoring implications
- Use `correctness_based` when correct answers are marked
- Partial credit can apply — selecting some but not all correct answers
- Set `autoScorable: true` when correct answers are defined

## Common mistakes
- Using multi_select when only one answer is correct — use single_select
- Too many choices (>8) — becomes overwhelming
- Not marking any choice as `correct` when using `correctness_based` scoring

## Pedagogy notes
Multi-select is harder than single_select because learners must evaluate every option independently — no process of elimination. Use when you want to assess comprehensive understanding of a category or set of properties.
