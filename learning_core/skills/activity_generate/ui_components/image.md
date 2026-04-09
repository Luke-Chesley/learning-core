# image

## Purpose
Displays a static image — diagram, photo, chart, or reference visual.

## When to use
- Providing a diagram or map that learners interact with (e.g., before label_map or hotspot_select)
- Showing a reference image for a science observation or art activity
- Displaying a chart or graph for analysis

## When not to use
- Decorative clip-art that adds no instructional value
- When no image URL is available (don't invent placeholder URLs)
- Purely digital text-based activities with no visual component

## Fields

| Field | Type | Required | Default | Notes |
|-------|------|----------|---------|-------|
| id | string | yes | — | Unique kebab-case |
| type | `"image"` | yes | — | |
| src | string | yes | — | Image URL; must be a real accessible URL |
| alt | string | yes | — | Descriptive alt text for accessibility |
| caption | string or null | no | null | Optional visible caption below the image |

## Example

```json
{
  "id": "diagram-water-cycle",
  "type": "image",
  "src": "https://example.com/water-cycle-diagram.png",
  "alt": "Diagram showing the water cycle: evaporation, condensation, precipitation, and collection",
  "caption": "The Water Cycle"
}
```

## Evidence implications
None — presentation only.

## Scoring implications
None.

## Common mistakes
- Inventing placeholder image URLs — only use real URLs from the input context
- Empty or generic alt text ("image") — describe what the image shows
- Using image when the activity has no visual assets provided

## Pedagogy notes
Images should serve the learning objective. Always write descriptive alt text so the activity remains accessible without the visual. If the image is essential for interaction (labeling, hotspot), pair it with the appropriate interactive component.
