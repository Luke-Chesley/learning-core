# Geography Pack

Use the geography pack for map-centered learning in geography, history, civics, migration, trade, and environmental studies.

This pack supports both:

- teaching artifacts: guided map exploration, compare views, annotated story maps, timeline maps
- learner interactions: select regions, place markers, trace routes, label map features

Prefer source-backed, cached geometry and engine-backed map widgets over freehand map JSON. Use the geography tools to inspect sources, fetch/cache geometry, build widgets, and validate configurations.

Escalate to `interactive_widget` with `surfaceKind="map_surface"` and `engineKind="map_geojson"` when the map itself is a core part of the learning experience. If a static image is enough, use standard components like `image`, `hotspot_select`, or `label_map`.
