# text_response

## Purpose
Multi-line text area for longer written responses — explanations, descriptions, paragraphs.

## When to use
- Learner needs to explain reasoning or process
- Written paragraph responses (e.g., "Describe how photosynthesis works")
- Journaling, summarizing, or paraphrasing
- When response length matters (use `minWords` to set expectations)

## When not to use
- Single-word or single-number answers — use short_answer
- Formatted writing with headings/lists — use rich_text_response
- Reflective sub-questions — use reflection_prompt

## Fields

| Field | Type | Required | Default | Notes |
|-------|------|----------|---------|-------|
| id | string | yes | — | Unique kebab-case |
| type | `"text_response"` | yes | — | |
| prompt | string | yes | — | The question or instruction |
| placeholder | string or null | no | null | Ghost text in text area |
| hint | string or null | no | null | Help text shown on request |
| minWords | integer or null | no | null | Minimum word count; must be > 0 if set |
| required | boolean | no | true | Whether learner must respond |

## Example

```json
{
  "id": "explain-process",
  "type": "text_response",
  "prompt": "In your own words, explain the steps of long division using the problem 156 / 12.",
  "placeholder": "Write at least three sentences...",
  "hint": "Think about: Divide, Multiply, Subtract, Bring down.",
  "minWords": 30,
  "required": true
}
```

## Evidence implications
- Produces `answer_response` evidence
- Always requires teacher review (no auto-scoring for free text)
- Rich evidence for understanding — shows reasoning, not just answers

## Scoring implications
- Typically `completion_based` or `rubric_based`
- Not suitable for `correctness_based` — free text can't be auto-checked
- Set `autoScorable: false`; set `requiresReview: true`

## Common mistakes
- Setting `minWords` too high for the age group — 20-30 words is substantial for young learners
- Using text_response when short_answer would suffice — signals to the learner they need to write more
- Prompt that asks for a single fact ("What year...?") — use short_answer

## Pedagogy notes
Text responses produce the richest evidence of understanding. Use when you want to see the learner's thinking process, not just a final answer. The `minWords` field sets expectations without being rigid. For younger learners, lower minWords or omit it to reduce pressure.
