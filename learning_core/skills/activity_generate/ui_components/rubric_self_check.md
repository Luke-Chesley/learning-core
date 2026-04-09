# rubric_self_check

## Purpose
Learner self-evaluates their work against defined criteria and quality levels. A structured self-assessment rubric.

## When to use
- Self-assessment against clear criteria (e.g., writing rubric, project rubric)
- When the learner should reflect on quality dimensions of their work
- Performance tasks where the teacher wants the learner's self-perception before review

## When not to use
- Teacher-only rubrics — use observation_record or teacher_checkoff
- Simple confidence check — use confidence_check
- Single-dimension rating — use rating

## Fields

| Field | Type | Required | Default | Notes |
|-------|------|----------|---------|-------|
| id | string | yes | — | Unique kebab-case |
| type | `"rubric_self_check"` | yes | — | |
| prompt | string or null | no | null | Instructions for self-evaluation |
| criteria | array of criterion objects | yes | — | Minimum 1 criterion |
| levels | array of level objects | yes | — | Minimum 2 levels (e.g., Beginning, Developing, Proficient) |
| notePrompt | string or null | no | null | Optional prompt for learner to add notes |

### Criterion object

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| id | string | yes | Unique within this component |
| label | string | yes | Criterion name (e.g., "Organization") |
| description | string or null | no | What this criterion measures |

### Level object

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| value | integer | yes | Numeric value (> 0); higher = better |
| label | string | yes | Level name (e.g., "Proficient") |
| description | string or null | no | What this level looks like |

## Example

```json
{
  "id": "rubric-essay",
  "type": "rubric_self_check",
  "prompt": "Rate your essay on each criterion:",
  "criteria": [
    { "id": "c-thesis", "label": "Thesis Statement", "description": "Clear, arguable claim" },
    { "id": "c-evidence", "label": "Supporting Evidence", "description": "Relevant facts or examples" },
    { "id": "c-organization", "label": "Organization", "description": "Logical flow of ideas" }
  ],
  "levels": [
    { "value": 1, "label": "Beginning", "description": "Needs significant revision" },
    { "value": 2, "label": "Developing", "description": "Shows understanding but incomplete" },
    { "value": 3, "label": "Proficient", "description": "Meets expectations" },
    { "value": 4, "label": "Advanced", "description": "Exceeds expectations" }
  ],
  "notePrompt": "What would you improve if you had more time?"
}
```

## Evidence implications
- Produces `rubric_score` evidence
- Each criterion gets a level rating from the learner
- Comparing self-assessment with teacher assessment reveals calibration

## Scoring implications
- Use `rubric_based` scoring mode
- Set `rubricMasteryLevel` in scoringModel (e.g., 3 for "Proficient")
- Not auto-scorable (self-assessment, not objective grading)

## Common mistakes
- Levels not in ascending order of quality
- Criteria too vague (e.g., "Quality" — be specific about what dimension)
- Only 2 levels (insufficient granularity for meaningful self-assessment)

## Pedagogy notes
Rubric self-checks build assessment literacy — learners learn what quality looks like. Effective when paired with a teacher review that compares the learner's self-assessment to the teacher's evaluation. Use clear, observable criteria that the learner can actually evaluate.
