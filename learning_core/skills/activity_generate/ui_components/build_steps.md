# build_steps

## Purpose
Scaffolded multi-step problem solving. Each step has an instruction and optional expected answer. The learner works through steps sequentially, building toward a solution.

## When to use
- Multi-step math problems (long division, equation solving)
- Science procedures with sequential steps
- Any task where scaffolding the process helps the learner
- "Worked example" style problems where the learner completes each stage

## When not to use
- Generic instruction delivery — build_steps is for active problem-solving
- Unordered tasks — use checklist
- Single-step responses — use short_answer
- Tasks where steps aren't naturally sequential

## Fields

| Field | Type | Required | Default | Notes |
|-------|------|----------|---------|-------|
| id | string | yes | — | Unique kebab-case |
| type | `"build_steps"` | yes | — | |
| prompt | string or null | no | null | Overall problem statement |
| workedExample | string or null | no | null | A worked example shown before the learner starts |
| steps | array of step objects | yes | — | Minimum 1 step |

### Step object

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| id | string | yes | Unique within this component |
| instruction | string | yes | What to do in this step |
| hint | string or null | no | Help text for this step |
| expectedValue | string or null | no | The expected answer for auto-checking |

## Example

```json
{
  "id": "build-division",
  "type": "build_steps",
  "prompt": "Solve 156 / 12 using long division:",
  "workedExample": "Example: 84 / 7 = 12. First divide 8 by 7 = 1 remainder 1. Bring down 4 to get 14. 14 / 7 = 2. Answer: 12.",
  "steps": [
    { "id": "step-1", "instruction": "How many times does 12 go into 15?", "hint": "12 x 1 = 12, 12 x 2 = 24", "expectedValue": "1" },
    { "id": "step-2", "instruction": "What is the remainder after subtracting 12 from 15?", "expectedValue": "3" },
    { "id": "step-3", "instruction": "Bring down the 6. What number do you now divide 12 into?", "expectedValue": "36" },
    { "id": "step-4", "instruction": "How many times does 12 go into 36?", "expectedValue": "3" },
    { "id": "step-5", "instruction": "What is the final answer?", "expectedValue": "13" }
  ]
}
```

## Evidence implications
- Produces `answer_response` evidence
- Each step with `expectedValue` can be individually checked
- Shows where in the process the learner gets stuck — powerful diagnostic

## Scoring implications
- Use `correctness_based` when steps have `expectedValue`
- Set `autoScorable: true` when expected values are provided
- Partial credit: fraction of steps completed correctly

## Common mistakes
- Using build_steps for simple instructions ("Read this, then read that") — not problem-solving
- Missing `expectedValue` on steps where auto-scoring is expected
- Too many steps (>8) — break into multiple build_steps or simplify
- Steps that aren't truly sequential — each step should build on the previous

## Pedagogy notes
Build_steps is the highest-engagement interactive component. It makes the learner's process visible — the teacher can see exactly where understanding breaks down. Use `workedExample` to model the process before the learner attempts it. Each step's instruction should be specific enough that the learner knows exactly what to compute or identify.
