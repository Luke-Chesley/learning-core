# checklist

## Purpose
A set of items the learner checks off as they complete tasks or confirm understanding. Items are unordered — completion order doesn't matter.

## When to use
- Step-by-step task completion where order is flexible
- "Did you remember to...?" verification lists
- Self-check before submission (e.g., "Review your work")
- Lab or project preparation checklists

## When not to use
- Order matters — use ordered_sequence instead
- Each item needs a detailed response — use multiple short_answer or text_response
- Teacher needs to verify — use teacher_checkoff instead

## Fields

| Field | Type | Required | Default | Notes |
|-------|------|----------|---------|-------|
| id | string | yes | — | Unique kebab-case |
| type | `"checklist"` | yes | — | |
| prompt | string or null | no | null | Optional instructions above the checklist |
| items | array of item objects | yes | — | Minimum 1 item |
| allowPartialSubmit | boolean | no | false | If true, learner can submit without checking all required items |

### Item object

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| id | string | yes | Unique within this component |
| label | string | yes | Text displayed next to the checkbox |
| description | string or null | no | Additional detail below the label |
| required | boolean | no (default true) | Whether this item must be checked |

## Example

```json
{
  "id": "prep-checklist",
  "type": "checklist",
  "prompt": "Before you begin the experiment, make sure you have:",
  "items": [
    { "id": "item-goggles", "label": "Safety goggles on", "required": true },
    { "id": "item-materials", "label": "All materials on your desk", "required": true },
    { "id": "item-notebook", "label": "Notebook open to a blank page", "required": true },
    { "id": "item-timer", "label": "Timer ready (optional)", "required": false }
  ],
  "allowPartialSubmit": false
}
```

## Evidence implications
- Produces `completion_marker` evidence
- Shows which items were completed / skipped
- Lightweight evidence — good for process tracking, not deep understanding

## Scoring implications
- Typically `completion_based` scoring
- Not auto-scorable in a correctness sense
- Set `autoScorable: false`

## Common mistakes
- Using checklist when ordering matters — use ordered_sequence
- Making every item required when some are truly optional — mark optional items with `required: false`
- Using a single-item checklist — that's just a checkbox, use it only if contextually appropriate

## Pedagogy notes
Checklists build executive function and self-regulation skills. They're especially valuable for younger learners who need help remembering preparation steps. Pair with offline activities for "did you do this?" verification.
