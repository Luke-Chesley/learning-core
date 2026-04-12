# map_surface / map_geojson

Use this widget when the lesson needs a real map interaction or a map-centered teaching artifact.
Back it with a real `sourceId`, not hand-authored fake geometry.

## Supported interaction modes

- `view_only`
- `guided_explore`
- `select_region`
- `multi_select_regions`
- `place_marker`
- `trace_path`
- `label_regions`
- `compare_layers`
- `timeline_scrub`

## Core ideas

- `layers` describe which source-backed features are visible.
- `state` stores current selections, marker placement, path drawing, labels, and timeline position.
- `evaluation` is optional for teaching artifacts but required for learner-input modes.

## Example

```json
{
  "surfaceKind": "map_surface",
  "engineKind": "map_geojson",
  "version": "1",
  "instructionText": "Select South America on the map.",
  "surface": {
    "projection": "equal_earth",
    "basemapStyle": "none",
    "center": { "lon": -15.0, "lat": 10.0 },
    "zoom": 2.5
  },
  "display": {
    "surfaceRole": "primary",
    "showLegend": true,
    "showLabels": true,
    "showInstructionsPanel": true,
    "allowLayerToggle": true
  },
  "state": {
    "sourceId": "geoboundaries:USA:ADM1",
    "activeLayerIds": ["geoboundaries-usa-adm1-base"],
    "selectedFeatureIds": [],
    "markerCoordinate": null,
    "drawnPath": [],
    "labelAssignments": {},
    "timelineYear": null
  },
  "interaction": {
    "mode": "select_region",
    "submissionMode": "explicit_submit",
    "allowReset": true,
    "resetPolicy": "reset_to_initial",
    "attemptPolicy": "allow_retry",
    "selectionBehavior": "single"
  },
  "feedback": {
    "mode": "explicit_submit",
    "displayMode": "inline"
  },
  "layers": [
    {
      "id": "geoboundaries-usa-adm1-base",
      "sourceId": "geoboundaries:USA:ADM1",
      "featureIds": ["california", "oregon", "washington"],
      "labelField": "shapeName",
      "visible": true,
      "stylePreset": "political"
    }
  ],
  "evaluation": {
    "acceptedFeatureIds": ["california"],
    "featureSelectionMode": "exact",
    "requiredCount": 1,
    "markerTarget": null,
    "expectedPath": null,
    "labelTargets": [],
    "minimumCoverage": 1.0
  },
  "annotations": {
    "legendTitle": "United States of America",
    "guidedPrompts": [],
    "callouts": [],
    "teacherNotes": null
  }
}
```
