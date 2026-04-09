# compare_and_explain

## Purpose
Learner compares two items and explains their reasoning. Tests analytical thinking — similarities, differences, trade-offs.

## When to use
- Comparing two concepts, methods, or examples
- Analyzing similarities and differences
- Critical thinking exercises ("Which approach is better and why?")
- Literary or scientific comparison tasks

## When not to use
- No clear comparison pair exists
- Simple factual recall — use short_answer or single_select
- Comparing more than two items — restructure or use text_response

## Fields

| Field | Type | Required | Default | Notes |
|-------|------|----------|---------|-------|
| id | string | yes | — | Unique kebab-case |
| type | `"compare_and_explain"` | yes | — | |
| prompt | string | yes | — | The comparison question |
| itemA | string | yes | — | First item to compare |
| itemB | string | yes | — | Second item to compare |
| responsePrompt | string or null | no | null | Specific guidance for the explanation (e.g., "Focus on differences") |
| required | boolean | no | true | |

## Example

```json
{
  "id": "compare-methods",
  "type": "compare_and_explain",
  "prompt": "Compare these two methods for solving 48 x 25:",
  "itemA": "Standard algorithm (multiply and carry)",
  "itemB": "Doubling and halving (48 x 25 = 24 x 50 = 12 x 100)",
  "responsePrompt": "Which method do you find easier? Explain why.",
  "required": true
}
```

## Evidence implications
- Produces `answer_response` evidence
- Rich analytical evidence — shows reasoning ability
- Requires teacher review

## Scoring implications
- Typically `rubric_based` or `completion_based`
- Not auto-scorable
- Set `requiresReview: true`

## Common mistakes
- Items that aren't meaningfully comparable
- Missing `responsePrompt` — without guidance, responses tend to be superficial
- Using when a simple text_response with a comparison question would suffice

## Pedagogy notes
Compare-and-explain develops higher-order thinking — analysis, evaluation, and synthesis. The structured format (item A vs. item B) gives learners a clear framework. Use `responsePrompt` to focus the analysis ("What's different?", "Which is better for...?", "When would you use each?").
