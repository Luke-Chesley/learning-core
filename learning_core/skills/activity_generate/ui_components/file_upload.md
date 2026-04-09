# file_upload

## Purpose
Learner uploads a file — document, image, PDF, or other artifact of their work.

## When to use
- Submitting completed worksheets or documents
- Uploading photos of physical work
- Turning in digital artifacts (presentations, spreadsheets)

## When not to use
- Specifically capturing a photo — use image_capture (camera-first UI)
- Specifically recording audio — use audio_capture
- Purely digital text responses — use text_response or rich_text_response

## Fields

| Field | Type | Required | Default | Notes |
|-------|------|----------|---------|-------|
| id | string | yes | — | Unique kebab-case |
| type | `"file_upload"` | yes | — | |
| prompt | string | yes | — | Instructions for what to upload |
| accept | array of strings or null | no | null | File type filters (e.g., `[".pdf", ".jpg", ".png"]`) |
| maxFiles | integer | no | 3 | Maximum files allowed (> 0) |
| notePrompt | string or null | no | null | Optional prompt for a text note alongside the upload |
| required | boolean | no | false | Whether upload is required for completion |

## Example

```json
{
  "id": "upload-worksheet",
  "type": "file_upload",
  "prompt": "Upload a photo or scan of your completed worksheet.",
  "accept": [".pdf", ".jpg", ".png"],
  "maxFiles": 1,
  "notePrompt": "Add any notes about your work (optional).",
  "required": false
}
```

## Evidence implications
- Produces `file_artifact` evidence
- Always requires teacher review (files can't be auto-scored)

## Scoring implications
- Typically `evidence_collected` or `teacher_observed` scoring
- Set `autoScorable: false`
- Set `requiresReview: true`

## Common mistakes
- Setting `required: true` for young learners who may not have scanning tools
- Missing `accept` filter — specify accepted types to prevent confusion
- Using file_upload when image_capture would be more intuitive for photos

## Pedagogy notes
File upload is the most flexible evidence capture — any format works. Use `notePrompt` to encourage the learner to describe what they uploaded, which aids teacher review. Keep `maxFiles` low (1-3) to set clear expectations.
