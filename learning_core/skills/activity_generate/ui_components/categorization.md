# categorization

## Purpose
Learner sorts items into named categories. Each item has one or more correct category assignments.

## When to use
- Classification tasks (e.g., "Sort these animals into vertebrates and invertebrates")
- Attribute-based grouping (e.g., "Which of these are solids, liquids, or gases?")
- Distinguishing between concept types

## When not to use
- Only 2 items — not enough to reveal a pattern
- Items naturally pair 1:1 — use matching_pairs
- Order within categories matters — use ordered_sequence per category
- Categories need rich descriptions — use sort_into_groups

## Fields

| Field | Type | Required | Default | Notes |
|-------|------|----------|---------|-------|
| id | string | yes | — | Unique kebab-case |
| type | `"categorization"` | yes | — | |
| prompt | string | yes | — | Instructions |
| categories | array of category objects | yes | — | Minimum 2 categories |
| items | array of item objects | yes | — | Minimum 2 items |
| hint | string or null | no | null | Help text |

### Category object

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| id | string | yes | Unique within this component |
| label | string | yes | Category name |

### Item object

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| id | string | yes | Unique within this component |
| text | string | yes | Display text |
| correctCategoryIds | array of strings | yes | One or more category IDs this item belongs to (min 1) |

## Example

```json
{
  "id": "cat-states",
  "type": "categorization",
  "prompt": "Sort each substance into the correct state of matter at room temperature:",
  "categories": [
    { "id": "solid", "label": "Solid" },
    { "id": "liquid", "label": "Liquid" },
    { "id": "gas", "label": "Gas" }
  ],
  "items": [
    { "id": "i-ice", "text": "Iron nail", "correctCategoryIds": ["solid"] },
    { "id": "i-water", "text": "Water", "correctCategoryIds": ["liquid"] },
    { "id": "i-oxygen", "text": "Oxygen", "correctCategoryIds": ["gas"] },
    { "id": "i-mercury", "text": "Mercury", "correctCategoryIds": ["liquid"] },
    { "id": "i-wood", "text": "Wooden block", "correctCategoryIds": ["solid"] }
  ],
  "hint": "Think about what state each substance is in at normal room temperature (about 20°C)."
}
```

## Evidence implications
- Produces `categorization_result` evidence
- Auto-scorable: each item placement is correct or not

## Scoring implications
- Use `correctness_based` scoring
- Set `autoScorable: true`
- Partial credit: fraction of items correctly categorized

## Common mistakes
- Items that could plausibly fit multiple categories without listing all correct ones in `correctCategoryIds`
- Too few items per category (aim for at least 2 per category to show a pattern)
- Categories that are too similar or overlapping

## Pedagogy notes
Categorization builds classification skills — a core scientific and analytical competency. Include at least 2 items per category so learners see patterns, not just memorize individual placements. Use when the learning objective involves distinguishing types, properties, or classes.
