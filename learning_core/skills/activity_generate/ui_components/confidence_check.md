# confidence_check

## Purpose
Five-level confidence self-assessment. The learner rates their understanding on a fixed 5-point scale.

## When to use
- After any learning activity to capture learner's self-perceived understanding
- As a metacognitive checkpoint mid-activity
- When learner confidence is informative for the teacher's next steps

## When not to use
- When you need custom scale labels — use rating instead
- For detailed self-evaluation with criteria — use rubric_self_check
- As a substitute for actual assessment — confidence is perception, not proof

## Fields

| Field | Type | Required | Default | Notes |
|-------|------|----------|---------|-------|
| id | string | yes | — | Unique kebab-case |
| type | `"confidence_check"` | yes | — | |
| prompt | string | no | `"How confident are you with this?"` | Override default prompt |
| labels | array of 5 strings | no | `["Not yet", "A little", "Getting there", "Pretty good", "Got it!"]` | Exactly 5 labels required |
| required | boolean | no | true | |

## Example

```json
{
  "id": "confidence-main",
  "type": "confidence_check",
  "prompt": "How well do you understand long division now?",
  "labels": ["Not yet", "A little", "Getting there", "Pretty good", "Got it!"]
}
```

## Evidence implications
- Produces `confidence_signal` evidence
- Useful for comparing with actual performance — reveals over/under-confidence
- Longitudinal tracking: trends in confidence over time

## Scoring implications
- Use `confidence_report` scoring mode when confidence is the primary signal
- Set `confidenceMasteryLevel` in scoringModel (e.g., 4 = "Pretty good" or higher)
- Not auto-scorable in a correctness sense

## Common mistakes
- Providing more or fewer than exactly 5 labels — must be exactly 5
- Omitting confidence_check entirely — include it whenever learner confidence is informative
- Using confidence_check as the only assessment — pair with actual evidence components

## Pedagogy notes
Confidence checks are lightweight and should be included in most activities (design rule 8). They help teachers identify learners who are confident but wrong (intervention needed) or unconfident but correct (encouragement needed). Place at the end of the activity after all interactive components.
