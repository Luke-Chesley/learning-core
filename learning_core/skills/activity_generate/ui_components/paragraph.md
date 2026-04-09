# paragraph

## Purpose
Renders a block of instructional or contextual text. Use sparingly to frame activity sections.

## When to use
- Brief context-setting before interactive components
- Short instructions the learner needs to read before responding
- Providing a passage or scenario for the learner to analyze

## When not to use
- Duplicating the lesson draft verbatim — the teacher already has that
- Long walls of text — learners skim; prefer callouts for key points
- Delivering the entire lesson content (this is an activity, not a textbook)

## Fields

| Field | Type | Required | Default | Notes |
|-------|------|----------|---------|-------|
| id | string | yes | — | Unique kebab-case |
| type | `"paragraph"` | yes | — | |
| text | string | yes | — | Plain text content |
| markdown | string or null | no | null | Markdown rendering; if set, takes precedence over `text` for display |

## Example

```json
{
  "id": "intro-context",
  "type": "paragraph",
  "text": "Read the following passage about the water cycle, then answer the questions below."
}
```

## Evidence implications
None — presentation only.

## Scoring implications
None.

## Common mistakes
- Using paragraphs to re-state the lesson plan (the teacher already sees it)
- Multiple long paragraphs in a row — break up with interactive components
- Setting `markdown` when plain `text` suffices

## Pedagogy notes
Keep paragraphs short and action-oriented. A good paragraph tells the learner what to do or provides just enough context for the next interactive component. If the text exceeds ~3 sentences, consider whether a callout or heading + shorter paragraph would work better.
