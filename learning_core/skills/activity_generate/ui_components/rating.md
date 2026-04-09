# rating

## Purpose
Numeric scale (typically 1-5) for subjective ratings — opinion, preference, agreement.

## When to use
- Likert-scale responses (agree/disagree, easy/hard)
- Subjective self-assessment that isn't confidence-specific
- Evaluating interest or engagement with a topic

## When not to use
- Measuring learner confidence — use confidence_check instead
- Factual correctness — use single_select or short_answer
- Detailed self-evaluation — use rubric_self_check

## Fields

| Field | Type | Required | Default | Notes |
|-------|------|----------|---------|-------|
| id | string | yes | — | Unique kebab-case |
| type | `"rating"` | yes | — | |
| prompt | string | yes | — | What to rate |
| min | integer | no | 1 | Low end of scale |
| max | integer | no | 5 | High end of scale |
| lowLabel | string or null | no | null | Label for the low end |
| highLabel | string or null | no | null | Label for the high end |
| required | boolean | no | true | |

## Example

```json
{
  "id": "rate-difficulty",
  "type": "rating",
  "prompt": "How difficult was this problem set for you?",
  "min": 1,
  "max": 5,
  "lowLabel": "Very easy",
  "highLabel": "Very challenging",
  "required": true
}
```

## Evidence implications
- Produces `self_assessment` evidence
- Captures subjective learner perception — useful for adaptive planning

## Scoring implications
- Typically `confidence_report` or `completion_based`
- Not auto-scorable (no correct answer)
- Provides signal for difficulty calibration, not mastery

## Common mistakes
- Using rating for factual assessment — it's for subjective responses only
- Missing lowLabel/highLabel — labels make the scale meaningful
- Confusing rating with confidence_check — use confidence_check for "how well do I understand this?"

## Pedagogy notes
Rating data helps teachers calibrate difficulty and engagement. Pair with a reflection_prompt to ask "why did you rate it that way?" for richer evidence. Most useful in post-activity or end-of-session contexts.
