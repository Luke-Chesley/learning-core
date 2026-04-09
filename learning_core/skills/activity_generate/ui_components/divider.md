# divider

## Purpose
Renders a horizontal rule to visually separate activity sections.

## When to use
- Between distinct activity phases when a heading feels too heavy
- Before a final reflection or summary section

## When not to use
- Between every component — creates visual clutter
- When a heading already provides sufficient separation
- In short activities (3 or fewer components)

## Fields

| Field | Type | Required | Default | Notes |
|-------|------|----------|---------|-------|
| id | string | yes | — | Unique kebab-case |
| type | `"divider"` | yes | — | |

## Example

```json
{
  "id": "div-before-reflection",
  "type": "divider"
}
```

## Evidence implications
None — presentation only.

## Scoring implications
None.

## Common mistakes
- Overuse — more than 2 dividers in a single activity is usually too many
- Using divider + heading together (pick one)

## Pedagogy notes
Dividers are the lightest-weight separator. Use headings for named sections and dividers for unnamed visual breaks.
