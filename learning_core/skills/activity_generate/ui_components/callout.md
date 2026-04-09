# callout

## Purpose
Highlighted box for tips, warnings, important notes, or safety information.

## When to use
- Key information the learner must notice (safety, important definitions)
- "Tip" or "Remember" boxes before a challenging component
- Warnings about common errors

## When not to use
- Generic encouragement ("You can do it!") — not informative
- Every section — overuse dilutes the visual signal
- Long instructional content — use paragraph instead

## Fields

| Field | Type | Required | Default | Notes |
|-------|------|----------|---------|-------|
| id | string | yes | — | Unique kebab-case |
| type | `"callout"` | yes | — | |
| variant | `"info"` `"tip"` `"warning"` `"note"` | no | `"info"` | Controls icon/color |
| text | string | yes | — | Plain text content |

## Example

```json
{
  "id": "tip-units",
  "type": "callout",
  "variant": "tip",
  "text": "Remember: always include units in your answer (e.g., 12 cm, not just 12)."
}
```

## Evidence implications
None — presentation only.

## Scoring implications
None.

## Common mistakes
- Overusing callouts — more than 2 per activity reduces their impact
- Using `"warning"` variant for non-critical information
- Placing a callout after the relevant component instead of before

## Pedagogy notes
Callouts are most effective when placed immediately before the component they support. Use `"warning"` for safety or error-prevention, `"tip"` for helpful strategies, `"info"` for definitions or context, and `"note"` for supplementary details.
