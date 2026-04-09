# hotspot_select

## Purpose
Learner clicks or taps specific regions on an image. Used for identifying areas, selecting features, or spatial recognition tasks.

## When to use
- "Click on the correct region" tasks (e.g., "Find the heart on the diagram")
- Geographic identification ("Click on France on the map")
- Selecting specific features in a visual

## When not to use
- No image is available — this component requires a real imageUrl
- Learner needs to type labels — use label_map instead
- Text-based identification — use single_select or short_answer

## Fields

| Field | Type | Required | Default | Notes |
|-------|------|----------|---------|-------|
| id | string | yes | — | Unique kebab-case |
| type | `"hotspot_select"` | yes | — | |
| prompt | string | yes | — | Instructions |
| imageUrl | string | yes | — | URL of the image; must be real and accessible |
| imageAlt | string | yes | — | Accessibility description |
| hotspots | array of hotspot objects | yes | — | Minimum 1 hotspot |
| requiredSelections | integer or null | no | null | How many hotspots to select (> 0) |
| hint | string or null | no | null | Help text |

### Hotspot object

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| id | string | yes | Unique within this component |
| x | float 0-100 | yes | Horizontal center as percentage |
| y | float 0-100 | yes | Vertical center as percentage |
| radius | float | no (default 5) | Hit area radius as percentage; must be > 0 |
| label | string | yes | Descriptive label (shown after selection or for accessibility) |
| correct | boolean or null | no | Whether this hotspot is a correct answer |

## Example

```json
{
  "id": "hs-continents",
  "type": "hotspot_select",
  "prompt": "Click on South America on the map.",
  "imageUrl": "https://example.com/world-map.png",
  "imageAlt": "Political world map showing all continents",
  "hotspots": [
    { "id": "hs-na", "x": 25, "y": 35, "radius": 12, "label": "North America", "correct": false },
    { "id": "hs-sa", "x": 30, "y": 65, "radius": 10, "label": "South America", "correct": true },
    { "id": "hs-eu", "x": 52, "y": 30, "radius": 8, "label": "Europe", "correct": false },
    { "id": "hs-af", "x": 55, "y": 55, "radius": 12, "label": "Africa", "correct": false }
  ],
  "requiredSelections": 1,
  "hint": "Look for the continent in the southern part of the Western Hemisphere."
}
```

## Evidence implications
- Produces `answer_response` evidence
- Auto-scorable when `correct` is marked on hotspots

## Scoring implications
- Use `correctness_based` scoring
- Set `autoScorable: true` when correct hotspots are marked

## Common mistakes
- Using without a real image URL
- Overlapping hotspots (ensure radii don't overlap significantly)
- Missing `correct` markers when using correctness_based scoring

## Pedagogy notes
Hotspot select tests spatial recognition — the learner must identify features visually, not just recall names. High interaction cost but engaging and effective for visual subjects. Ensure hotspot radii are large enough for touch screens.
