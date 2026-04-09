# construction_space

## Purpose
Open-ended building or free-form creation space. The learner constructs a product — a sentence, a formula, a diagram description, or any creative output.

## When to use
- Creative construction tasks ("Build a sentence using these vocabulary words")
- Open-ended problem solving where the answer format is flexible
- Constructing an argument, proof, or explanation from scratch
- Activities where the process of construction is the learning

## When not to use
- Structured recall — use short_answer or single_select
- Step-by-step scaffolded work — use build_steps
- Simple text writing — use text_response

## Fields

| Field | Type | Required | Default | Notes |
|-------|------|----------|---------|-------|
| id | string | yes | — | Unique kebab-case |
| type | `"construction_space"` | yes | — | |
| prompt | string | yes | — | What to construct |
| scaffoldText | string or null | no | null | Pre-populated starter text or framework |
| hint | string or null | no | null | Help text |
| required | boolean | no | true | |

## Example

```json
{
  "id": "construct-sentence",
  "type": "construction_space",
  "prompt": "Build a compound sentence using 'although' to connect two ideas about the water cycle.",
  "scaffoldText": "Although __________, __________.",
  "hint": "A compound sentence with 'although' has a dependent clause and an independent clause.",
  "required": true
}
```

## Evidence implications
- Produces `construction_product` evidence
- The constructed product is the evidence — rich and open-ended
- Always requires teacher review

## Scoring implications
- Typically `rubric_based` or `completion_based`
- Not auto-scorable (creative/open-ended output)
- Set `requiresReview: true`

## Common mistakes
- Using without `scaffoldText` when learners need structure — scaffolding helps younger learners start
- Prompt too vague ("Create something about science") — be specific about the construction task
- Using construction_space for simple answers that could use short_answer

## Pedagogy notes
Construction space is the highest-interaction-cost component. It tests creation-level thinking (top of Bloom's taxonomy). Use `scaffoldText` to lower the entry barrier while still requiring genuine construction. The prompt should clearly define what "done" looks like so the learner knows the scope of their creation.
