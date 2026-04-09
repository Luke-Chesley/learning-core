# label_map

## Purpose
Learner labels specific points on an image — typing the correct text for each marked position. Used for diagram labeling.

## When to use
- Labeling parts of a diagram (anatomy, geography, machine parts)
- Identifying features on a map or chart
- Science diagrams where position matters

## When not to use
- No image is available — this component requires a real imageUrl
- Clicking/selecting regions — use hotspot_select instead
- Simple text identification without spatial context — use short_answer

## Fields

| Field | Type | Required | Default | Notes |
|-------|------|----------|---------|-------|
| id | string | yes | — | Unique kebab-case |
| type | `"label_map"` | yes | — | |
| prompt | string | yes | — | Instructions |
| imageUrl | string | yes | — | URL of the image to label; must be real and accessible |
| imageAlt | string | yes | — | Accessibility description |
| labels | array of label objects | yes | — | Minimum 1 label point |

### Label object

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| id | string | yes | Unique within this component |
| x | float 0-100 | yes | Horizontal position as percentage |
| y | float 0-100 | yes | Vertical position as percentage |
| correctText | string | yes | The expected label text |
| hint | string or null | no | Per-label hint |

## Example

```json
{
  "id": "label-cell",
  "type": "label_map",
  "prompt": "Label the parts of the plant cell shown in the diagram:",
  "imageUrl": "https://example.com/plant-cell-diagram.png",
  "imageAlt": "Diagram of a plant cell with arrows pointing to key organelles",
  "labels": [
    { "id": "l-nucleus", "x": 50, "y": 40, "correctText": "Nucleus", "hint": "The control center of the cell" },
    { "id": "l-cell-wall", "x": 10, "y": 50, "correctText": "Cell wall", "hint": "The rigid outer boundary" },
    { "id": "l-chloroplast", "x": 70, "y": 60, "correctText": "Chloroplast", "hint": "Where photosynthesis happens" }
  ]
}
```

## Evidence implications
- Produces `answer_response` evidence
- Each label can be auto-scored against `correctText`

## Scoring implications
- Use `correctness_based` scoring
- Set `autoScorable: true`
- Partial credit: fraction of labels correctly filled

## Common mistakes
- Using without a real image URL — don't invent placeholder URLs
- Coordinates outside 0-100 range
- Labels too close together (ensure at least 10% spacing between points)

## Pedagogy notes
Label maps test spatial knowledge — the learner must connect concepts to physical positions. High interaction cost but very effective for anatomy, geography, and diagram-heavy subjects. Only use when you have a real image to work with.
