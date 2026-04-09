# single_select

## Purpose
Multiple-choice question where the learner picks exactly one answer from a set of options.

## When to use
- Testing recall of a specific fact with one correct answer
- Check-for-understanding after instruction
- Diagnostic: identifying common misconceptions via distractor analysis

## When not to use
- Multiple correct answers exist — use multi_select
- Subjective preference — use rating
- Open-ended responses — use short_answer or text_response
- Avoid spamming: don't chain 5+ single_select components in a row

## Fields

| Field | Type | Required | Default | Notes |
|-------|------|----------|---------|-------|
| id | string | yes | — | Unique kebab-case |
| type | `"single_select"` | yes | — | |
| prompt | string | yes | — | The question |
| choices | array of choice objects | yes | — | Minimum 2 choices |
| immediateCorrectness | boolean | no | false | Show correct/incorrect immediately on selection |
| hint | string or null | no | null | Help text |
| required | boolean | no | true | |

### Choice object

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| id | string | yes | Unique within this component |
| text | string | yes | Display text for the choice |
| correct | boolean or null | no | Mark the correct answer; stripped before showing to learner |
| explanation | string or null | no | Shown after answer if `immediateCorrectness` is true |

## Example

```json
{
  "id": "q-photosynthesis",
  "type": "single_select",
  "prompt": "Which gas do plants absorb during photosynthesis?",
  "choices": [
    { "id": "a", "text": "Oxygen", "correct": false, "explanation": "Plants release oxygen, not absorb it." },
    { "id": "b", "text": "Carbon dioxide", "correct": true, "explanation": "Correct! Plants absorb CO2 and use it to make glucose." },
    { "id": "c", "text": "Nitrogen", "correct": false, "explanation": "Nitrogen is abundant in air but not used in photosynthesis." },
    { "id": "d", "text": "Hydrogen", "correct": false }
  ],
  "immediateCorrectness": true,
  "required": true
}
```

## Evidence implications
- Produces `answer_response` evidence
- With `correct` markings, enables auto-scoring
- Distractor choices reveal misconceptions to the teacher

## Scoring implications
- Use `correctness_based` when `correct` is marked on choices
- Set `autoScorable: true` when correct answers are defined
- `masteryThreshold` applies to the percentage of correct single_select answers across the activity

## Common mistakes
- Only 2 choices (true/false style) when 3-4 would reduce guessing
- All distractors obviously wrong — make them plausible to test real understanding
- Missing `correct: true` on exactly one choice when using `correctness_based` scoring
- Chaining many single_select in a row — feels like a quiz, not a learning activity

## Pedagogy notes
Most effective for retrieval practice and misconception diagnosis. Use `immediateCorrectness: true` for formative feedback, `false` for assessment. Write distractors based on common errors students make — each wrong choice should represent a real misconception. Include `explanation` on all choices to turn every answer into a learning moment.
