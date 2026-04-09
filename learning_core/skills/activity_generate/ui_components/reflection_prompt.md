# reflection_prompt

## Purpose
Structured metacognitive reflection with one or more sub-questions. Each sub-prompt can ask for text or a rating response.

## When to use
- End-of-activity reflection ("What did you find hardest?")
- Metacognitive check-ins tied to the lesson's success criteria
- Multi-faceted reflection where you want separate responses to distinct questions
- Connecting learning to personal experience or prior knowledge

## When not to use
- Single open-ended question — use text_response instead
- Factual assessment — use short_answer, single_select, etc.
- Generic "what did you learn?" without grounding in success criteria

## Fields

| Field | Type | Required | Default | Notes |
|-------|------|----------|---------|-------|
| id | string | yes | — | Unique kebab-case |
| type | `"reflection_prompt"` | yes | — | |
| prompt | string | yes | — | Overall reflection context or framing |
| subPrompts | array of sub-prompt objects | yes | — | Minimum 1 sub-prompt |
| required | boolean | no | true | |

### Sub-prompt object

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| id | string | yes | Unique within this component |
| text | string | yes | The sub-question |
| responseKind | `"text"` or `"rating"` | no (default `"text"`) | Type of response expected |

## Example

```json
{
  "id": "reflect-main",
  "type": "reflection_prompt",
  "prompt": "Think about what you practiced today with long division.",
  "subPrompts": [
    { "id": "sp-hard", "text": "Which step of the D-M-S-B process was hardest for you?", "responseKind": "text" },
    { "id": "sp-strategy", "text": "What strategy did you use when you got stuck?", "responseKind": "text" },
    { "id": "sp-effort", "text": "How much effort did this take?", "responseKind": "rating" }
  ],
  "required": true
}
```

## Evidence implications
- Produces `reflection_response` evidence
- Each sub-prompt response is captured individually
- Rich qualitative evidence for teacher review

## Scoring implications
- Typically `completion_based` — reflection has no correct answer
- Not auto-scorable
- Set `requiresReview: true` for meaningful teacher engagement

## Common mistakes
- Generic sub-prompts not grounded in the lesson ("What did you learn?") — tie to specific success criteria
- Too many sub-prompts (>4) — becomes tedious; keep to 2-3
- Using reflection_prompt for a single question — use text_response; reflection_prompt's value is multi-faceted structured reflection

## Pedagogy notes
Effective reflection prompts reference specific lesson content and success criteria. Instead of "What did you learn?", ask "Which of the three water cycle stages was easiest to explain in your own words?" This grounds reflection in observable learning and gives the teacher actionable signal.
