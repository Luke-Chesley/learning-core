# Chess Examples

## Best move with board input

Use `interactive_widget(board_surface/chess)` for the move itself. Keep `evaluation.expectedMoves` bounded to the acceptable moves.

Make the board primary, keep side to move explicit, and pair the move with a nearby reasoning component only when the lesson genuinely needs explanation.

## Compare and explain around a position

Use a board widget for the position and `compare_and_explain` for two candidate moves. This keeps the widget focused and captures reasoning separately.

## Confidence check after analysis

After a move-selection or plan-selection task, a brief `confidence_check` can capture calibration without turning the activity into trivia.

## Reflection prompt after a mistake pattern

If the lesson is about recurring tactical misses or endgame habits, use a brief `reflection_prompt` after the core board task.

## Text-only chess, used sparingly

Use plain components without a board only when the learning target does not depend on a live position.
