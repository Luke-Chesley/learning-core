# board_surface + chess

Use this widget spec when a chess position is central to the activity and the learner should inspect the board or submit a move.

## Purpose

Render a board from canonical backend state and capture learner move input in a bounded payload. Backend chess logic remains the source of truth.

## Use when

- Best-move, tactic, threat, plan, or endgame technique questions depend on a real position.
- The learner should submit a move as evidence.
- Board-centered reasoning is more authentic than abstract trivia.

## Avoid when

- The task is better as a plain explanation or comparison prompt.
- The position is not central to the evidence.
- You only need a textual chess fact or vocabulary check.

## Exact fields

```json
{
  "surfaceKind": "board_surface",
  "engineKind": "chess",
  "version": "1",
  "surface": {
    "orientation": "white"
  },
  "display": {
    "showSideToMove": true,
    "showCoordinates": true,
    "showMoveHint": true,
    "boardRole": "primary"
  },
  "state": {
    "fen": "string"
  },
  "interaction": {
    "mode": "view_only | move_input",
    "submissionMode": "immediate | explicit_submit",
    "selectionMode": "click_click | drag_drop | either",
    "showLegalTargets": true,
    "allowReset": true,
    "resetPolicy": "not_allowed | reset_to_initial",
    "attemptPolicy": "single_attempt | allow_retry"
  },
  "feedback": {
    "mode": "none | immediate | explicit_submit",
    "displayMode": "inline | banner"
  },
  "evaluation": {
    "expectedMoves": ["SAN or UCI"]
  },
  "annotations": {
    "highlightSquares": ["e4", "f7"],
    "arrows": [
      { "fromSquare": "d1", "toSquare": "h5", "color": "green" }
    ]
  }
}
```

## Examples

### Best move

```json
{
  "surfaceKind": "board_surface",
  "engineKind": "chess",
  "version": "1",
  "surface": { "orientation": "white" },
  "display": {
    "showSideToMove": true,
    "showCoordinates": true,
    "showMoveHint": true,
    "boardRole": "primary"
  },
  "state": { "fen": "4k3/8/8/8/8/8/4Q3/4K3 w - - 0 1" },
  "interaction": {
    "mode": "move_input",
    "submissionMode": "immediate",
    "selectionMode": "click_click",
    "showLegalTargets": true,
    "allowReset": true,
    "resetPolicy": "reset_to_initial",
    "attemptPolicy": "allow_retry"
  },
  "feedback": { "mode": "immediate", "displayMode": "inline" },
  "evaluation": { "expectedMoves": ["Qb5+", "e2b5"] },
  "annotations": { "highlightSquares": [], "arrows": [] }
}
```

### Threat identification with board context

Use a board widget plus nearby `compare_and_explain` or `text_response`. The widget can hold the position while the text component captures reasoning.

## Expected-move guidance

- Include `evaluation.expectedMoves` only when the activity has bounded target moves.
- Prefer SAN plus UCI when that makes authoring clearer.
- If multiple moves are acceptable, include all of them.
- If `interaction.mode` is `move_input`, make the board the primary evidence and keep side to move obvious in display or prompt.

## Evidence implications

- The main evidence is the learner's submitted move or board action.
- If reasoning matters, pair the widget with a text component instead of overloading the widget.

## Runtime feedback implications

- Bounded move evaluation should happen through the separate runtime feedback path.
- Legal targets and move normalization should come from the backend transition path, not the frontend.
- Backend chess logic should normalize SAN and UCI.
- Do not rely on frontend chess libraries as the canonical evaluator.

## Common mistakes

- Using the board for trivia that does not depend on the position.
- Omitting the FEN.
- Hiding side to move in both display and prompt.
- Using view-only mode when the learner should submit a move.
- Packing explanation, move entry, and reflection into one widget instead of combining the widget with normal components.
