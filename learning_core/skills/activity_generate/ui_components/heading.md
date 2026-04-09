# heading

## Purpose
Renders a section heading to visually break the activity into named parts.

## When to use
- Separating distinct phases (e.g., "Warm-Up", "Practice", "Reflect")
- Activities with 3+ interactive components that benefit from grouping

## When not to use
- Single-section activities — a heading alone adds visual noise
- Never as the only component; always pair with content below it

## Fields

| Field | Type | Required | Default | Notes |
|-------|------|----------|---------|-------|
| id | string | yes | — | Unique kebab-case |
| type | `"heading"` | yes | — | |
| level | integer 1-4 | no | 2 | 1 = largest; activity titles are typically level 2 |
| text | string | yes | — | Plain text, no markdown |

## Example

```json
{
  "id": "section-practice",
  "type": "heading",
  "level": 2,
  "text": "Practice Problems"
}
```

## Evidence implications
None — presentation only.

## Scoring implications
None.

## Common mistakes
- Using level 1 for every heading (reserve level 1 for major titles)
- Adding a heading before a single component — unnecessary structure

## Pedagogy notes
Good headings help the teacher see activity structure at a glance and help the learner understand progression through the activity.
