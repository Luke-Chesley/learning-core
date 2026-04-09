# short_answer

## Purpose
Single-line text input for brief factual responses — a word, number, phrase, or short sentence.

## When to use
- Recall of a specific fact, term, or value
- Fill-in-the-blank style questions
- Numeric answers (e.g., "What is 7 x 8?")
- Vocabulary: "What word means...?"

## When not to use
- Open-ended reflection or opinion — use text_response or reflection_prompt
- When there are discrete answer options — use single_select instead
- Multi-sentence answers — use text_response

## Fields

| Field | Type | Required | Default | Notes |
|-------|------|----------|---------|-------|
| id | string | yes | — | Unique kebab-case |
| type | `"short_answer"` | yes | — | |
| prompt | string | yes | — | The question or instruction |
| placeholder | string or null | no | null | Ghost text in input field |
| hint | string or null | no | null | Shown on request or after wrong attempt |
| expectedAnswer | string or null | no | null | Canonical correct answer for auto-scoring |
| required | boolean | no | true | Whether learner must answer to complete |

## Example

```json
{
  "id": "q-capital-france",
  "type": "short_answer",
  "prompt": "What is the capital of France?",
  "placeholder": "Type your answer...",
  "hint": "It's the city known as the City of Light.",
  "expectedAnswer": "Paris",
  "required": true
}
```

## Evidence implications
- Produces `answer_response` evidence
- If `expectedAnswer` is set, the response can be compared for correctness
- Without `expectedAnswer`, evidence is captured but requires teacher review

## Scoring implications
- Use `correctness_based` scoring when `expectedAnswer` is provided
- Use `completion_based` when there's no single correct answer
- Set `autoScorable: true` only when `expectedAnswer` is provided

## Common mistakes
- Missing `expectedAnswer` when using `correctness_based` scoring — the system can't auto-score without it
- Prompt that requires a paragraph response — use text_response instead
- Using short_answer for opinion questions (e.g., "What do you think about...?")

## Pedagogy notes
Short answer is strongest for retrieval practice — pulling facts from memory strengthens retention. Pair with a hint for scaffolded practice. For young learners, include a placeholder showing the expected format (e.g., "e.g., 42 cm").
