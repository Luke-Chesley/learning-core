# graph_surface + graphing

Use this widget spec when graph interaction is central evidence and simpler components would flatten the task too much.

## Purpose

Represent graph interaction in a bounded widget so backend graph logic can later own evaluation.

## Use when

- Plotting, interpreting, or comparing graphs is itself the learning target.
- The learner should place points, sketch a relationship, or inspect a graph-based representation.

## Avoid when

- A static image plus `short_answer` or `compare_and_explain` is enough.
- The graph is decorative rather than central evidence.

## Exact fields

```json
{
  "surfaceKind": "graph_surface",
  "engineKind": "graphing",
  "version": "1",
  "surface": {
    "xLabel": "x",
    "yLabel": "y",
    "grid": true
  },
  "state": {
    "prompt": "Plot the line y = 2x + 1",
    "initialExpression": ""
  },
  "interaction": {
    "mode": "plot_curve"
  },
  "evaluation": {
    "expectedGraphDescription": "line with slope 2 and intercept 1"
  },
  "annotations": {
    "overlayText": "Graph the relationship."
  }
}
```

## Evidence implications

- Use only when graph interaction is the actual evidence.
- Pair with explanation components if the learner should justify the graph.

## Runtime feedback implications

- Keep runtime feedback separate from generation.
- This widget exists now so graph-native evaluation can slot in later without changing the top-level activity contract.

## Common mistakes

- Using this widget when a static graph image would do.
- Treating it as a generic drawing canvas.
- Inventing fields outside the bounded payload.

