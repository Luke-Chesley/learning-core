# rich_text_response

## Purpose
Rich-text editor for formatted writing — supports bold, italic, lists, headings within the response.

## When to use
- Essay writing or report drafting
- Creative writing where formatting matters
- Responses that naturally include lists, structure, or emphasis
- Older learners practicing document composition

## When not to use
- Simple paragraph responses — use text_response (less UI overhead)
- Short factual answers — use short_answer
- Young learners who don't need formatting tools

## Fields

| Field | Type | Required | Default | Notes |
|-------|------|----------|---------|-------|
| id | string | yes | — | Unique kebab-case |
| type | `"rich_text_response"` | yes | — | |
| prompt | string | yes | — | The writing prompt or instruction |
| hint | string or null | no | null | Help text shown on request |
| required | boolean | no | true | Whether learner must respond |

## Example

```json
{
  "id": "essay-draft",
  "type": "rich_text_response",
  "prompt": "Write a short persuasive paragraph arguing for or against year-round schooling. Use bold for your main claim.",
  "hint": "Start with your claim, then give two supporting reasons.",
  "required": true
}
```

## Evidence implications
- Produces `answer_response` evidence
- Always requires teacher review
- Captures richer formatting intent than plain text_response

## Scoring implications
- Typically `rubric_based` — evaluate structure, argument quality, formatting use
- Not auto-scorable
- Set `requiresReview: true`

## Common mistakes
- Using for short responses that don't need formatting — unnecessary UI complexity
- Using for young learners (K-2) who can't leverage formatting tools

## Pedagogy notes
Reserve for activities where document structure is part of the learning objective (essay writing, report formatting). For most written responses, text_response is simpler and more appropriate.
