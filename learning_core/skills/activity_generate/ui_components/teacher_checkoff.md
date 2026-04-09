# teacher_checkoff

## Purpose
Teacher or parent confirms the learner demonstrated specific skills or completed specific tasks. A lightweight verification tool.

## When to use
- Teacher confirms learner demonstrated a skill live
- Parent verifies learner completed an offline task
- Quick verification checkpoints during hybrid activities
- "Teacher, please confirm:" moments in guided activities

## When not to use
- Detailed observations needed — use observation_record
- Learner self-completion tracking — use checklist
- No teacher/parent available to verify

## Fields

| Field | Type | Required | Default | Notes |
|-------|------|----------|---------|-------|
| id | string | yes | — | Unique kebab-case |
| type | `"teacher_checkoff"` | yes | — | |
| prompt | string | yes | — | Instructions for the teacher/parent |
| items | array of item objects | yes | — | Minimum 1 item to check off |
| acknowledgmentLabel | string or null | no | null | Label for the final acknowledgment (e.g., "I confirm...") |
| notePrompt | string or null | no | null | Optional prompt for teacher notes |

### Item object

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| id | string | yes | Unique within this component |
| label | string | yes | What to verify |
| description | string or null | no | Additional detail |

## Example

```json
{
  "id": "verify-experiment",
  "type": "teacher_checkoff",
  "prompt": "Parent/Teacher: Please verify the following after watching the learner:",
  "items": [
    { "id": "v-setup", "label": "Set up the experiment correctly" },
    { "id": "v-measure", "label": "Measured ingredients accurately" },
    { "id": "v-record", "label": "Recorded observations in notebook" }
  ],
  "acknowledgmentLabel": "I confirm the learner completed these steps.",
  "notePrompt": "Any additional observations?"
}
```

## Evidence implications
- Produces `teacher_checkoff` evidence
- Each item is checked or not — binary verification
- Light but authoritative evidence from an adult observer

## Scoring implications
- Typically `teacher_observed` scoring mode
- Not auto-scorable (requires human verification)

## Common mistakes
- Confusing with checklist (learner completes) vs. teacher_checkoff (adult verifies)
- Too many items (>5) — keep focused on key demonstrations

## Pedagogy notes
Teacher checkoff is the simplest form of human verification. It's especially valuable for offline activities where the digital system can't observe what happened. The acknowledgment label creates a clear moment of confirmation. Keep items specific and observable — "demonstrated proper grip" not "understood the concept."
