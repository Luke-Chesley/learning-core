# expression_surface + math_symbolic

Use this widget spec when the learner needs to enter structured symbolic math and a plain text box would lose important signal.

## Purpose

Capture symbolic math input in a bounded structure so backend math logic can later validate or compare it.

## Use when

- Algebraic expressions, equations, or symbolic simplification are central evidence.
- Exact structure matters more than prose.
- A normal `short_answer` would be too lossy.

## Avoid when

- A plain number or short label is enough.
- The main target is explanation, reflection, or error diagnosis in prose.
- Frontend math rendering is not necessary to collect the evidence.

## Exact fields

```json
{
  "surfaceKind": "expression_surface",
  "engineKind": "math_symbolic",
  "version": "1",
  "surface": {
    "placeholder": "x = ?",
    "mathKeyboard": true
  },
  "state": {
    "promptLatex": "2x + 3 = 11",
    "initialValue": ""
  },
  "interaction": {
    "mode": "expression_entry"
  },
  "evaluation": {
    "expectedExpression": "x=4",
    "equivalenceMode": "equivalent"
  },
  "annotations": {
    "helperText": "Enter the full solved expression."
  }
}
```

## Evidence implications

- Use this when symbolic structure is the evidence.
- Pair it with `text_response` or `build_steps` if explanation also matters.

## Runtime feedback implications

- Keep runtime evaluation separate from authoring.
- Deterministic symbolic evaluation can be added later without changing the activity shape.

## Common mistakes

- Using this widget for plain arithmetic that fits `short_answer`.
- Replacing all explanation with symbolic entry.
- Inventing unsupported fields outside the documented payload.

