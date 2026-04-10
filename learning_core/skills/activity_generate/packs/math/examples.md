# Math Examples

## Arithmetic fluency

Use `short_answer` for the result, plus `confidence_check` only if confidence is instructionally useful.

## Fractions

If the learner is comparing or simplifying fractions symbolically, consider `interactive_widget(expression_surface/math_symbolic)`; otherwise `short_answer` or `compare_and_explain` is often enough.

## Long division

`build_steps` works well for quotient, multiply, subtract, and bring-down phases. Add one targeted reflection or explanation prompt if the lesson emphasizes reasoning.

## Algebra steps

If symbolic entry matters, use `interactive_widget(expression_surface/math_symbolic)` with a nearby `text_response` only when the learner must justify the move.

## Geometry labeling

Use `label_map` for parts of a shape or diagram. Pair it with `short_answer` only if the learner also needs to compute or explain something.

## Word problems

Use a small coherent sequence: a brief framing paragraph, one `build_steps` or `text_response`, and maybe a final `short_answer` for the computed result.

