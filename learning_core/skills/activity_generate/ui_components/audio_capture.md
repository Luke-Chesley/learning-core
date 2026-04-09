# audio_capture

## Purpose
Learner records an audio response — verbal explanation, oral reading, pronunciation practice, or narration.

## When to use
- Oral reading fluency assessment
- Verbal explanation of a concept
- Foreign language pronunciation practice
- Young learners who can speak more fluently than they write

## When not to use
- Text responses are more appropriate for the age group and subject
- Learner doesn't have microphone access
- The activity is purely written

## Fields

| Field | Type | Required | Default | Notes |
|-------|------|----------|---------|-------|
| id | string | yes | — | Unique kebab-case |
| type | `"audio_capture"` | yes | — | |
| prompt | string | yes | — | What to record |
| maxDurationSeconds | integer or null | no | null | Maximum recording length (> 0) |
| required | boolean | no | false | Whether recording is required |

## Example

```json
{
  "id": "read-aloud",
  "type": "audio_capture",
  "prompt": "Read the following passage aloud at your normal reading pace.",
  "maxDurationSeconds": 120,
  "required": false
}
```

## Evidence implications
- Produces `audio_artifact` evidence
- Requires teacher review — audio can't be auto-scored

## Scoring implications
- Typically `teacher_observed` or `evidence_collected`
- Set `autoScorable: false`
- Set `requiresReview: true`

## Common mistakes
- Missing `maxDurationSeconds` for young learners — set a limit to prevent very long recordings
- Setting `required: true` when microphone access isn't guaranteed

## Pedagogy notes
Audio capture is valuable for early readers, language learners, and any activity where verbal fluency is the learning objective. For young learners, keep maxDurationSeconds short (30-60s) to maintain focus. Pair with a text-based reflection for a complete picture.
