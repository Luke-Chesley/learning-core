# Chess Pack

Use this pack when the request is clearly about chess.

## What strong chess activities do

- Prefer board-centered tasks over abstract trivia when a position is central.
- Focus on candidate moves, plans, threats, tactics, evaluation, or endgame technique.
- Capture evidence from an actual position when the learner should inspect or play a move.
- Use text-only chess sparingly and only when the board is not the main evidence.

## Stay simple when the board is not central

Normal components often fit:

- `compare_and_explain` for comparing two plans or moves
- `text_response` for explaining why a move works
- `confidence_check` for calibration after analysis
- `reflection_prompt` for reviewing a mistake pattern

## Escalate when the position is central

Use `interactive_widget` with `surfaceKind="board_surface"` and `engineKind="chess"` when:

- the learner should submit a move
- the position itself is the evidence
- board inspection materially improves the task

Do not escalate when the task is really a vocabulary or history question.

## Compose around the board

The board widget should usually do one bounded job well. Put explanation, confidence, and reflection in normal components around it instead of overloading the widget.

