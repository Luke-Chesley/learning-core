# Math Pack

Use this pack when the request is clearly about math.

## What strong math activities do

- Put the mathematical idea at the center, not generic quiz churn.
- Capture evidence that shows whether the learner can solve, explain, classify, or diagnose.
- Balance correctness with reasoning. Some tasks need the final answer; others need explanation or error analysis.
- Use procedural scaffolding when the target is a process the learner is still building.
- Ask for explanation when reasoning matters to the lesson goal, not as filler after every problem.

## Stay simple first

Prefer normal components when they are enough:

- `short_answer` for compact numeric or label answers
- `build_steps` for scaffolded multi-step work
- `compare_and_explain` for contrasting strategies or examples
- `reflection_prompt` or `confidence_check` when metacognition matters

## Escalate to widgets only when needed

- Use `interactive_widget` with `surfaceKind="expression_surface"` and `engineKind="math_symbolic"` when structured symbolic input matters more than plain text.
- Use `interactive_widget` with `surfaceKind="graph_surface"` and `engineKind="graphing"` when graph interaction is central evidence.
- Do not escalate to a widget just to make the activity feel more advanced.

## Avoid quiz spam

- Do not turn every math activity into a stack of disconnected single-select items.
- Prefer a few coherent tasks over many shallow prompts.
- If the learner should explain thinking, make that explanation specific and tied to the math move or pattern.

## Meaningful math evidence

Strong evidence can be:

- a correct final answer when the target is fluency
- a sequence of intermediate steps when process matters
- an explanation of why a move works
- identification of an error and how to fix it
- a graph or symbolic entry when the representation itself matters

