# image_capture

## Purpose
Camera-first interface for the learner to photograph physical work — art projects, lab setups, handwriting, real-world observations.

## When to use
- Capturing evidence of hands-on work (art, experiments, construction)
- Photographing handwritten solutions
- Documenting real-world observations (nature walk, field trip)
- Hybrid activities where physical work needs digital evidence

## When not to use
- Uploading existing files or documents — use file_upload
- Purely digital activities with no physical component
- Activities where the learner doesn't have camera access

## Fields

| Field | Type | Required | Default | Notes |
|-------|------|----------|---------|-------|
| id | string | yes | — | Unique kebab-case |
| type | `"image_capture"` | yes | — | |
| prompt | string | yes | — | What to photograph |
| instructions | string or null | no | null | Tips for taking a good photo |
| maxImages | integer | no | 3 | Maximum images allowed (> 0) |
| required | boolean | no | false | Whether capture is required |

## Example

```json
{
  "id": "photo-experiment",
  "type": "image_capture",
  "prompt": "Take a photo of your completed experiment setup.",
  "instructions": "Make sure the whole setup is visible and well-lit.",
  "maxImages": 2,
  "required": false
}
```

## Evidence implications
- Produces `image_artifact` evidence
- Requires teacher review — images can't be auto-scored

## Scoring implications
- Typically `evidence_collected` or `teacher_observed`
- Set `autoScorable: false`
- Set `requiresReview: true`

## Common mistakes
- Setting `required: true` when camera access isn't guaranteed
- Missing `instructions` — learners (especially younger) need guidance on what makes a good photo

## Pedagogy notes
Image capture bridges the gap between physical and digital learning. Essential for offline/hybrid activities where the evidence is physical work. The `instructions` field is important for younger learners — guide them toward a clear, useful photograph rather than a blurry snapshot.
