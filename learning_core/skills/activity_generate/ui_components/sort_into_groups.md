# sort_into_groups

## Purpose
Learner drags items into described groups. Similar to categorization but groups can have richer descriptions and each item belongs to exactly one group.

## When to use
- Grouping where category descriptions help the learner understand the criteria
- When categories need more context than a simple label
- Sorting with explanatory group definitions

## When not to use
- Simple label-only categories — use categorization (lighter)
- Items belong to multiple groups — use categorization with multiple correctCategoryIds
- Only a binary split (2 items) — too trivial

## Fields

| Field | Type | Required | Default | Notes |
|-------|------|----------|---------|-------|
| id | string | yes | — | Unique kebab-case |
| type | `"sort_into_groups"` | yes | — | |
| prompt | string | yes | — | Instructions |
| groups | array of group objects | yes | — | Minimum 2 groups |
| items | array of item objects | yes | — | Minimum 2 items |
| hint | string or null | no | null | Help text |

### Group object

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| id | string | yes | Unique within this component |
| label | string | yes | Group name |
| description | string or null | no | Explanation of what belongs in this group |

### Item object

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| id | string | yes | Unique within this component |
| text | string | yes | Display text |
| correctGroupId | string | yes | Exactly one group ID |

## Example

```json
{
  "id": "sort-sentences",
  "type": "sort_into_groups",
  "prompt": "Sort each sentence into the correct type:",
  "groups": [
    { "id": "fact", "label": "Fact", "description": "A statement that can be proven true or false with evidence" },
    { "id": "opinion", "label": "Opinion", "description": "A statement that reflects a personal belief or preference" }
  ],
  "items": [
    { "id": "s1", "text": "The Earth orbits the Sun.", "correctGroupId": "fact" },
    { "id": "s2", "text": "Pizza is the best food.", "correctGroupId": "opinion" },
    { "id": "s3", "text": "Water boils at 100°C at sea level.", "correctGroupId": "fact" },
    { "id": "s4", "text": "Summer is the best season.", "correctGroupId": "opinion" }
  ]
}
```

## Evidence implications
- Produces `categorization_result` evidence
- Auto-scorable: each item placement is correct or not

## Scoring implications
- Use `correctness_based` scoring
- Set `autoScorable: true`

## Common mistakes
- Confusing with categorization — use sort_into_groups when group descriptions add value; use categorization for simpler label-only categories
- Items that genuinely could go in multiple groups — each item must have one clear group

## Pedagogy notes
The group descriptions serve as scaffolding — they remind the learner of the sorting criteria. This is better than plain categorization when the categories are conceptual rather than factual (e.g., "fact vs. opinion" benefits from explicit definitions).
