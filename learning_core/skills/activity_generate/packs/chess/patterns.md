# Chess Patterns

## Best move

Use `interactive_widget(board_surface/chess)` as the primary widget with bounded expected moves when the target is a concrete move choice. Make side to move obvious and keep the board central.

## Identify the tactical motif

Use a primary board widget for the position, then `compare_and_explain` or `text_response` for the tactical idea if reasoning matters.

## Compare two candidate moves

Show the position in a primary board widget and pair it with `compare_and_explain` so the learner justifies which move is stronger.

## Find the threat

Use the board widget when the threat depends on the position, then ask for a short explanation nearby if needed.

## Choose a plan

Board plus `choose_next_step` or `compare_and_explain` works well for plan selection from a concrete position, but the board should still be the main evidence surface.

## Blunder-check routine

Use the board to anchor the position, then ask what threat or tactical refutation the learner should notice. Do not reduce the board to a decorative reference if the lesson depends on move choice.

## Endgame technique

Use a board widget when the exact setup matters. Keep the prompt concrete: opposition, promotion race, king activity, or conversion plan.
