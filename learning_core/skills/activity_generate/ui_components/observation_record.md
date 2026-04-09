# observation_record

## Purpose
Structured observation form — typically filled by a teacher or parent watching the learner. Captures qualitative and quantitative observations.

## When to use
- Teacher observes a learner demonstrating a skill (e.g., reading aloud, performing a lab)
- Parent records observations during offline activity
- Structured clinical observations in special education settings
- Learner self-observation in guided activities

## When not to use
- Learner-driven digital activities — observation_record is primarily for an observer
- Simple yes/no verification — use teacher_checkoff
- When no teacher/parent is present to observe

## Fields

| Field | Type | Required | Default | Notes |
|-------|------|----------|---------|-------|
| id | string | yes | — | Unique kebab-case |
| type | `"observation_record"` | yes | — | |
| prompt | string | yes | — | What to observe |
| fields | array of field objects | yes | — | Minimum 1 field |
| filledBy | `"teacher"` `"parent"` `"learner"` | no | `"teacher"` | Who fills out the record |

### Field object

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| id | string | yes | Unique within this component |
| label | string | yes | What to observe/record |
| inputKind | `"text"` `"rating"` `"checkbox"` | no (default `"text"`) | Input type for this field |

## Example

```json
{
  "id": "obs-reading",
  "type": "observation_record",
  "prompt": "Observe the learner reading aloud and record the following:",
  "fields": [
    { "id": "f-fluency", "label": "Reading fluency", "inputKind": "rating" },
    { "id": "f-expression", "label": "Expression and intonation", "inputKind": "rating" },
    { "id": "f-errors", "label": "Errors or mispronunciations noted", "inputKind": "text" },
    { "id": "f-self-correct", "label": "Self-corrected errors?", "inputKind": "checkbox" }
  ],
  "filledBy": "parent"
}
```

## Evidence implications
- Produces `teacher_observation` evidence
- Always requires review — observation is the review
- Rich qualitative data about demonstrated skill

## Scoring implications
- Typically `teacher_observed` scoring mode
- Not auto-scorable
- The observation itself is the assessment

## Common mistakes
- Using observation_record for learner-only activities — it needs an observer
- Too many fields (>6) — keep focused on the key observable behaviors
- Using when teacher_checkoff (simpler) would suffice

## Pedagogy notes
Observation records capture what tests cannot — fluency, confidence, physical skill, social interaction. Design fields around observable behaviors, not inferred mental states. Rating fields give quick quantitative data; text fields capture qualitative detail.
