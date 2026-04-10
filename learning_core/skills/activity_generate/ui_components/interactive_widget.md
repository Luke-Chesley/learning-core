# interactive_widget

`interactive_widget` is the bounded host component for richer engine-backed interaction surfaces. Use it only when a standard component would make the activity meaningfully weaker.

## Use when

- The learning target depends on interacting with a structured surface, not just typing or selecting.
- Backend domain logic should own canonical state or evaluation.
- A board, symbolic math entry surface, or graph surface is central evidence.

## Avoid when

- A standard component already captures the evidence cleanly.
- The task is mostly explanation, comparison, or reflection.
- The surface would be decorative instead of instructionally necessary.

## Top-level fields

- `type`: always `interactive_widget`
- `id`: unique kebab-case identifier
- `prompt`: concise learner-facing prompt
- `required`: whether the learner must interact with it
- `widget`: the nested typed payload

## Nested widget payload

The nested `widget` object is bounded and typed. It includes:

- `surfaceKind`
- `engineKind`
- `version`
- `surface`
- `state`
- `interaction`
- `evaluation`
- `annotations`

Do not invent other top-level fields. Read the matching widget spec for exact fields and examples.

## When to escalate

Escalate to `interactive_widget` only when the richer surface materially improves the learning interaction. Prefer simple components when they are enough.

Good reasons:

- The learner must inspect and play a move from a board position.
- The learner must enter structured symbolic math, not just prose.
- Graph interaction is itself the evidence.

Bad reasons:

- Making the activity feel fancier.
- Replacing a clear `short_answer` with an overbuilt surface.
- Using a widget when a text explanation is the real target.

## Example

```json
{
  "type": "interactive_widget",
  "id": "best-move",
  "prompt": "White to move. Find the best move.",
  "required": true,
  "widget": {
    "surfaceKind": "board_surface",
    "engineKind": "chess",
    "version": "1",
    "surface": { "orientation": "white" },
    "state": { "fen": "4k3/8/8/8/8/8/4Q3/4K3 w - - 0 1" },
    "interaction": { "mode": "move_input" },
    "evaluation": { "expectedMoves": ["Qb5+", "e2b5"] },
    "annotations": {
      "highlightSquares": [],
      "arrows": []
    }
  }
}
```

## Evidence and runtime feedback

- `interactive_widget` should still fit the strict activity contract.
- Runtime learner feedback happens separately from authoring.
- Use `evaluation` only for bounded evaluation targets, not for hidden prompts or freeform instructions.

