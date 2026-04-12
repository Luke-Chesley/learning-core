from __future__ import annotations

import json
import math
import re
import tempfile
import zipfile
from io import BytesIO
from pathlib import Path
from typing import Any

import httpx

try:
    import folium
except Exception:  # pragma: no cover - optional dependency
    folium = None

try:
    from geopy.geocoders import Nominatim
except Exception:  # pragma: no cover - optional dependency
    Nominatim = None

try:
    from pyproj import Transformer
except Exception:  # pragma: no cover - optional dependency
    Transformer = None


GEOGRAPHY_USER_AGENT = "learning-core-geography-pack/0.1"
_GEOboundaries_ID_PATTERN = re.compile(r"^geoboundaries:([A-Z]{3}|ALL):(ADM[0-5])$")


def serialize(payload: object) -> str:
    return json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True)


def list_sources() -> list[dict[str, Any]]:
    return [
        {
            "sourceId": "geoboundaries:USA:ADM1",
            "provider": "geoBoundaries",
            "title": "United States first-order administrative boundaries",
            "notes": "Accurate state boundaries sourced from the Census-backed geoBoundaries feed.",
        },
        {
            "sourceId": "geoboundaries:FRA:ADM1",
            "provider": "geoBoundaries",
            "title": "France first-order administrative boundaries",
            "notes": "Useful for country-scale regional geography lessons.",
        },
        {
            "sourceId": "geoboundaries:EGY:ADM1",
            "provider": "geoBoundaries",
            "title": "Egypt first-order administrative boundaries",
            "notes": "Useful for Nile and North Africa lessons.",
        },
        {
            "template": "geoboundaries:<ISO3>:<ADM0-ADM5>",
            "provider": "geoBoundaries",
            "title": "Dynamic administrative boundary source",
            "notes": "Use any ISO-3 country code plus an ADM level. Example: geoboundaries:BRA:ADM1",
        },
    ]


def describe_source(source_id: str, refresh: bool = False) -> dict[str, Any]:
    descriptor = resolve_source_descriptor(source_id)
    collection_bundle = fetch_source_collection(source_id, refresh=refresh)
    feature_names = [feature_name(feature) for feature in collection_bundle["featureCollection"]["features"][:12]]
    return {
        **descriptor,
        "featureCount": len(collection_bundle["featureCollection"]["features"]),
        "featureSample": feature_names,
        "cachePath": collection_bundle["cachePath"],
        "metadata": collection_bundle["metadata"],
    }


def lookup_feature(source_id: str, query: str, refresh: bool = False) -> dict[str, Any]:
    bundle = fetch_source_collection(source_id, refresh=refresh)
    normalized_query = query.strip().lower()
    for feature in bundle["featureCollection"]["features"]:
        name = feature_name(feature).lower()
        if normalized_query in {name, str(feature["id"]).lower()}:
            return {
                "sourceId": source_id,
                "featureId": feature["id"],
                "name": feature_name(feature),
                "properties": feature.get("properties", {}),
                "centroid": feature_centroid(feature),
            }
    raise KeyError(f"No feature matched '{query}' in source '{source_id}'.")


def build_widget_config(
    *,
    source_id: str,
    interaction_mode: str,
    feature_ids: list[str] | None = None,
    prompt_text: str | None = None,
    compare_source_id: str | None = None,
    timeline_years: list[int] | None = None,
    refresh: bool = False,
) -> dict[str, Any]:
    bundle = fetch_source_collection(source_id, refresh=refresh)
    selected_ids = resolve_feature_ids(bundle["featureCollection"], feature_ids)
    active_layer_id = f"{safe_layer_id(source_id)}-base"
    center = collection_center(bundle["featureCollection"], selected_ids)
    widget: dict[str, Any] = {
        "surfaceKind": "map_surface",
        "engineKind": "map_geojson",
        "version": "1",
        "instructionText": prompt_text or f"Use the map from {bundle['metadata'].get('boundaryName', source_id)}.",
        "surface": {
            "projection": "equal_earth",
            "basemapStyle": "none",
            "center": {"lon": center["lon"], "lat": center["lat"]},
            "zoom": 4.0 if len(selected_ids) <= 5 else 3.0,
            "bounds": None,
        },
        "display": {
            "surfaceRole": "primary" if interaction_mode not in {"view_only", "guided_explore", "compare_layers", "timeline_scrub"} else "supporting",
            "showLegend": True,
            "showLabels": True,
            "showInstructionsPanel": True,
            "allowLayerToggle": True,
        },
        "state": {
            "sourceId": source_id,
            "activeLayerIds": [active_layer_id],
            "selectedFeatureIds": [],
            "markerCoordinate": None,
            "drawnPath": [],
            "labelAssignments": {},
            "timelineYear": timeline_years[0] if timeline_years else None,
        },
        "interaction": {
            "mode": interaction_mode,
            "submissionMode": "explicit_submit" if interaction_mode not in {"view_only", "guided_explore", "compare_layers", "timeline_scrub"} else "immediate",
            "allowReset": interaction_mode not in {"guided_explore", "compare_layers", "timeline_scrub"},
            "resetPolicy": "reset_to_initial" if interaction_mode not in {"guided_explore", "compare_layers", "timeline_scrub"} else "not_allowed",
            "attemptPolicy": "allow_retry",
            "selectionBehavior": "single" if interaction_mode == "select_region" else "multiple",
        },
        "feedback": {
            "mode": "explicit_submit" if interaction_mode not in {"view_only", "guided_explore", "compare_layers", "timeline_scrub"} else "none",
            "displayMode": "inline",
        },
        "layers": [
            {
                "id": active_layer_id,
                "sourceId": source_id,
                "featureIds": selected_ids,
                "labelField": preferred_label_field(bundle["featureCollection"]),
                "visible": True,
                "stylePreset": "political",
            }
        ],
        "evaluation": {
            "acceptedFeatureIds": selected_ids if interaction_mode in {"select_region", "multi_select_regions"} else [],
            "featureSelectionMode": "exact",
            "requiredCount": len(selected_ids) if interaction_mode == "multi_select_regions" else (1 if interaction_mode == "select_region" else None),
            "markerTarget": None,
            "expectedPath": None,
            "labelTargets": [],
            "minimumCoverage": 1.0,
        },
        "annotations": {
            "legendTitle": bundle["metadata"].get("boundaryName") or source_id,
            "guidedPrompts": [],
            "callouts": [],
            "teacherNotes": None,
        },
    }
    if compare_source_id:
        compare_bundle = fetch_source_collection(compare_source_id, refresh=refresh)
        widget["layers"].append(
            {
                "id": f"{safe_layer_id(compare_source_id)}-compare",
                "sourceId": compare_source_id,
                "featureIds": [feature["id"] for feature in compare_bundle["featureCollection"]["features"]],
                "labelField": preferred_label_field(compare_bundle["featureCollection"]),
                "visible": True,
                "stylePreset": "historical",
            }
        )
    if interaction_mode == "place_marker":
        target_feature = feature_by_id(bundle["featureCollection"], selected_ids[0])
        widget["evaluation"]["markerTarget"] = {
            "coordinate": feature_centroid(target_feature),
            "toleranceKm": 50.0,
        }
    if interaction_mode == "label_regions":
        widget["evaluation"]["labelTargets"] = [
            {"featureId": feature_id, "correctLabel": feature_name(feature_by_id(bundle["featureCollection"], feature_id))}
            for feature_id in selected_ids
        ]
    if interaction_mode == "trace_path":
        raise ValueError("trace_path requires a route-oriented source provider and is not yet supported for geoboundaries sources.")
    if timeline_years:
        widget["annotations"]["guidedPrompts"].append(
            f"Use the timeline control to compare {', '.join(str(year) for year in timeline_years)}."
        )
    return widget


def validate_widget_config(widget_payload: dict[str, Any], refresh: bool = False) -> dict[str, Any]:
    result: dict[str, Any] = {"valid": True, "errors": [], "warnings": []}
    state = widget_payload.get("state", {})
    source_id = state.get("sourceId")
    if not source_id:
        return {"valid": False, "errors": ["state.sourceId is required."], "warnings": []}
    try:
        bundle = fetch_source_collection(source_id, refresh=refresh)
    except Exception as error:
        return {"valid": False, "errors": [str(error)], "warnings": []}

    available_feature_ids = {feature["id"] for feature in bundle["featureCollection"]["features"]}
    layers = widget_payload.get("layers", [])
    interaction = widget_payload.get("interaction", {})
    evaluation = widget_payload.get("evaluation", {})
    mode = interaction.get("mode")

    if not layers:
        result["valid"] = False
        result["errors"].append("Map widgets require at least one layer.")

    for layer in layers:
        layer_source_id = layer.get("sourceId")
        if not layer_source_id:
            result["valid"] = False
            result["errors"].append(f"Layer '{layer.get('id', 'unknown')}' must include sourceId.")
            continue
        try:
            layer_bundle = fetch_source_collection(layer_source_id, refresh=refresh)
        except Exception as error:
            result["valid"] = False
            result["errors"].append(str(error))
            continue
        layer_feature_ids = {feature["id"] for feature in layer_bundle["featureCollection"]["features"]}
        missing = [feature_id for feature_id in layer.get("featureIds", []) if feature_id not in layer_feature_ids]
        if missing:
            result["valid"] = False
            result["errors"].append(
                f"Layer '{layer.get('id', 'unknown')}' references unknown feature ids: {', '.join(missing)}"
            )

    if mode in {"select_region", "multi_select_regions"}:
        accepted_ids = evaluation.get("acceptedFeatureIds") or []
        if not accepted_ids:
            result["valid"] = False
            result["errors"].append(f"{mode} requires evaluation.acceptedFeatureIds.")
        missing = [feature_id for feature_id in accepted_ids if feature_id not in available_feature_ids]
        if missing:
            result["valid"] = False
            result["errors"].append(f"Accepted feature ids are missing from source '{source_id}': {', '.join(missing)}")
    if mode == "place_marker" and not evaluation.get("markerTarget"):
        result["valid"] = False
        result["errors"].append("place_marker requires evaluation.markerTarget.")
    if mode == "label_regions" and not evaluation.get("labelTargets"):
        result["valid"] = False
        result["errors"].append("label_regions requires evaluation.labelTargets.")
    if mode == "compare_layers" and len(layers) < 2:
        result["valid"] = False
        result["errors"].append("compare_layers requires at least two layers.")
    if mode == "trace_path":
        result["warnings"].append("trace_path currently needs a route source provider instead of administrative boundaries.")

    result["sourceTitle"] = bundle["metadata"].get("boundaryName") or source_id
    result["availableFeatures"] = sorted(list(available_feature_ids))[:200]
    return result


def evaluate_feature_selection(
    *,
    accepted_feature_ids: list[str],
    learner_feature_ids: list[str],
    selection_mode: str = "exact",
) -> dict[str, Any]:
    expected = set(accepted_feature_ids)
    learner = set(learner_feature_ids)
    matched = len(expected & learner)
    if not expected:
        return {"status": "needs_review", "score": None, "matchedTargets": 0, "totalTargets": 0}
    if selection_mode == "superset_ok" and expected.issubset(learner):
        return {"status": "correct", "score": 1.0, "matchedTargets": len(expected), "totalTargets": len(expected)}
    if learner == expected:
        return {"status": "correct", "score": 1.0, "matchedTargets": len(expected), "totalTargets": len(expected)}
    if matched > 0:
        return {"status": "partial", "score": matched / len(expected), "matchedTargets": matched, "totalTargets": len(expected)}
    return {"status": "incorrect", "score": 0.0, "matchedTargets": 0, "totalTargets": len(expected)}


def evaluate_marker(*, learner_coordinate: dict[str, float] | None, target_coordinate: dict[str, Any] | None) -> dict[str, Any]:
    if learner_coordinate is None or target_coordinate is None:
        return {"status": "needs_review", "score": None, "matchedTargets": 0, "totalTargets": 1}
    target = target_coordinate["coordinate"]
    tolerance_km = float(target_coordinate.get("toleranceKm", 50.0))
    distance_km = haversine_km(learner_coordinate["lat"], learner_coordinate["lon"], target["lat"], target["lon"])
    if distance_km <= tolerance_km:
        return {"status": "correct", "score": 1.0, "matchedTargets": 1, "totalTargets": 1, "distanceKm": distance_km}
    return {"status": "incorrect", "score": 0.0, "matchedTargets": 0, "totalTargets": 1, "distanceKm": distance_km}


def evaluate_path(*, learner_points: list[dict[str, float]], expected_path: dict[str, Any] | None) -> dict[str, Any]:
    if expected_path is None:
        return {"status": "needs_review", "score": None, "matchedTargets": 0, "totalTargets": 1}
    expected_points = expected_path.get("coordinates") or []
    if len(learner_points) < 2 or len(expected_points) < 2:
        return {"status": "incorrect", "score": 0.0, "matchedTargets": 0, "totalTargets": 1}
    tolerance_km = float(expected_path.get("toleranceKm", 100.0))
    endpoint_error = max(
        haversine_km(learner_points[0]["lat"], learner_points[0]["lon"], expected_points[0]["lat"], expected_points[0]["lon"]),
        haversine_km(learner_points[-1]["lat"], learner_points[-1]["lon"], expected_points[-1]["lat"], expected_points[-1]["lon"]),
    )
    if endpoint_error <= tolerance_km:
        return {"status": "correct", "score": 1.0, "matchedTargets": 1, "totalTargets": 1, "endpointErrorKm": endpoint_error}
    return {"status": "incorrect", "score": 0.0, "matchedTargets": 0, "totalTargets": 1, "endpointErrorKm": endpoint_error}


def evaluate_labels(*, learner_labels: dict[str, str], label_targets: list[dict[str, str]]) -> dict[str, Any]:
    if not label_targets:
        return {"status": "needs_review", "score": None, "matchedTargets": 0, "totalTargets": 0}
    matched = sum(
        1
        for target in label_targets
        if learner_labels.get(target["featureId"], "").strip().lower() == target["correctLabel"].strip().lower()
    )
    status = "correct" if matched == len(label_targets) else "partial" if matched > 0 else "incorrect"
    return {"status": status, "score": matched / len(label_targets), "matchedTargets": matched, "totalTargets": len(label_targets)}


def generate_guided_artifact(
    *,
    source_id: str,
    focus_feature_ids: list[str] | None = None,
    title: str,
    prompt: str,
    compare_source_id: str | None = None,
    refresh: bool = False,
) -> dict[str, Any]:
    widget = build_widget_config(
        source_id=source_id,
        interaction_mode="guided_explore",
        feature_ids=focus_feature_ids,
        prompt_text=prompt,
        compare_source_id=compare_source_id,
        refresh=refresh,
    )
    widget["display"]["surfaceRole"] = "supporting"
    widget["annotations"]["guidedPrompts"] = [
        "Look for the outer shape first.",
        "Notice how the borders cluster or separate areas.",
        "Use the labels and overlays to explain what the map is showing.",
    ]
    return {
        "title": title,
        "components": [
            {"type": "paragraph", "id": "map-brief", "text": prompt},
            {
                "type": "interactive_widget",
                "id": "map-guided-artifact",
                "prompt": prompt,
                "required": False,
                "widget": widget,
            },
            {
                "type": "reflection_prompt",
                "id": "map-reflect",
                "prompt": "What border or regional pattern stands out most in this map?",
                "required": True,
            },
        ],
    }


def render_preview_html(widget_payload: dict[str, Any], refresh: bool = False) -> dict[str, Any]:
    if folium is None:
        return {"available": False, "message": "Preview export requires the optional 'folium' dependency."}
    center = widget_payload["surface"]["center"]
    map_view = folium.Map(location=[center["lat"], center["lon"]], zoom_start=widget_payload["surface"].get("zoom", 3))
    for layer in widget_payload.get("layers", []):
        bundle = fetch_source_collection(layer["sourceId"], refresh=refresh)
        feature_ids = set(layer.get("featureIds") or [feature["id"] for feature in bundle["featureCollection"]["features"]])
        feature_collection = {
            "type": "FeatureCollection",
            "features": [feature for feature in bundle["featureCollection"]["features"] if feature["id"] in feature_ids],
        }
        folium.GeoJson(feature_collection, name=layer["id"]).add_to(map_view)
    folium.LayerControl().add_to(map_view)
    tmp_dir = Path(tempfile.mkdtemp(prefix="learning-core-map-preview-"))
    output_path = tmp_dir / "preview.html"
    map_view.save(str(output_path))
    return {"available": True, "path": str(output_path)}


def geocode_place(place_name: str) -> dict[str, Any]:
    if Nominatim is None:
        return {"available": False, "message": "Geocoding enrichment requires the optional 'geopy' dependency."}
    geocoder = Nominatim(user_agent=GEOGRAPHY_USER_AGENT)
    result = geocoder.geocode(place_name, exactly_one=True)
    if result is None:
        return {"available": True, "found": False, "query": place_name}
    return {
        "available": True,
        "found": True,
        "query": place_name,
        "name": result.address,
        "coordinate": {"lat": result.latitude, "lon": result.longitude},
    }


def project_coordinate(lon: float, lat: float, *, from_crs: str = "EPSG:4326", to_crs: str = "EPSG:3857") -> dict[str, Any]:
    if Transformer is not None:
        transformer = Transformer.from_crs(from_crs, to_crs, always_xy=True)
        x, y = transformer.transform(lon, lat)
        return {"x": x, "y": y, "fromCrs": from_crs, "toCrs": to_crs, "method": "pyproj"}
    if from_crs == "EPSG:4326" and to_crs == "EPSG:3857":
        radius = 6378137.0
        x = radius * math.radians(lon)
        y = radius * math.log(math.tan(math.pi / 4.0 + math.radians(lat) / 2.0))
        return {"x": x, "y": y, "fromCrs": from_crs, "toCrs": to_crs, "method": "fallback_web_mercator"}
    raise ValueError("Coordinate projection requires pyproj for this CRS transformation.")


def resolve_source_descriptor(source_id: str) -> dict[str, Any]:
    match = _GEOboundaries_ID_PATTERN.fullmatch(source_id)
    if match:
        country, level = match.groups()
        return {
            "sourceId": source_id,
            "provider": "geoBoundaries",
            "country": country,
            "level": level,
            "metadataEndpoint": f"https://www.geoboundaries.org/api/current/gbOpen/{country}/{level}/",
            "cacheKey": safe_layer_id(source_id),
        }
    raise ValueError(f"Unsupported sourceId '{source_id}'. Expected format like geoboundaries:USA:ADM1")


def fetch_source_collection(source_id: str, refresh: bool = False) -> dict[str, Any]:
    descriptor = resolve_source_descriptor(source_id)
    cache_dir = cache_root() / descriptor["cacheKey"]
    cache_dir.mkdir(parents=True, exist_ok=True)
    metadata_path = cache_dir / "metadata.json"
    collection_path = cache_dir / "features.geojson"
    if not refresh and metadata_path.exists() and collection_path.exists():
        return {
            "sourceId": source_id,
            "metadata": json.loads(metadata_path.read_text(encoding="utf-8")),
            "featureCollection": json.loads(collection_path.read_text(encoding="utf-8")),
            "cachePath": str(cache_dir),
        }

    with httpx.Client(timeout=30.0, headers={"User-Agent": GEOGRAPHY_USER_AGENT}, follow_redirects=True) as client:
        metadata_response = client.get(descriptor["metadataEndpoint"])
        metadata_response.raise_for_status()
        metadata = metadata_response.json()
        download_link = metadata.get("staticDownloadLink")
        if not isinstance(download_link, str) or not download_link:
            raise ValueError(f"Source '{source_id}' did not provide a usable staticDownloadLink.")
        zip_response = client.get(download_link)
        zip_response.raise_for_status()

    feature_collection = extract_feature_collection_from_zip(zip_response.content)
    normalized_collection = normalize_feature_collection(feature_collection)
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=True, indent=2, sort_keys=True), encoding="utf-8")
    collection_path.write_text(json.dumps(normalized_collection, ensure_ascii=True), encoding="utf-8")
    return {
        "sourceId": source_id,
        "metadata": metadata,
        "featureCollection": normalized_collection,
        "cachePath": str(cache_dir),
    }


def extract_feature_collection_from_zip(zip_bytes: bytes) -> dict[str, Any]:
    with zipfile.ZipFile(BytesIO(zip_bytes)) as archive:
        preferred_names = [name for name in archive.namelist() if name.endswith("_simplified.geojson")]
        candidate_names = preferred_names or [name for name in archive.namelist() if name.endswith(".geojson")]
        if not candidate_names:
            raise ValueError("Downloaded source archive did not contain a GeoJSON file.")
        with archive.open(candidate_names[0]) as handle:
            return json.load(handle)


def normalize_feature_collection(feature_collection: dict[str, Any]) -> dict[str, Any]:
    normalized = {"type": "FeatureCollection", "features": []}
    used_ids: set[str] = set()
    for index, feature in enumerate(feature_collection.get("features", [])):
        properties = dict(feature.get("properties", {}))
        feature_id = slugify(
            str(
                properties.get("shapeID")
                or properties.get("shapeName")
                or properties.get("name")
                or properties.get("NAME")
                or f"feature-{index + 1}"
            )
        )
        if feature_id in used_ids:
            feature_id = f"{feature_id}-{index + 1}"
        used_ids.add(feature_id)
        normalized["features"].append(
            {
                "type": "Feature",
                "id": feature_id,
                "properties": properties,
                "geometry": feature.get("geometry"),
            }
        )
    return normalized


def feature_name(feature: dict[str, Any]) -> str:
    properties = feature.get("properties", {})
    return str(
        properties.get("shapeName")
        or properties.get("name")
        or properties.get("NAME")
        or properties.get("shapeID")
        or feature.get("id")
    )


def preferred_label_field(feature_collection: dict[str, Any]) -> str:
    if not feature_collection.get("features"):
        return "id"
    properties = feature_collection["features"][0].get("properties", {})
    for candidate in ("shapeName", "name", "NAME", "shapeID"):
        if candidate in properties:
            return candidate
    return "id"


def feature_by_id(feature_collection: dict[str, Any], feature_id: str) -> dict[str, Any]:
    for feature in feature_collection.get("features", []):
        if feature["id"] == feature_id:
            return feature
    raise KeyError(f"Unknown feature id '{feature_id}'.")


def resolve_feature_ids(feature_collection: dict[str, Any], feature_ids: list[str] | None) -> list[str]:
    all_ids = [feature["id"] for feature in feature_collection.get("features", [])]
    if not feature_ids:
        return all_ids
    resolved: list[str] = []
    for feature_id in feature_ids:
        feature_by_id(feature_collection, feature_id)
        if feature_id not in resolved:
            resolved.append(feature_id)
    return resolved


def feature_centroid(feature: dict[str, Any]) -> dict[str, float]:
    points = _flatten_geometry_points(feature.get("geometry") or {})
    lon = sum(point[0] for point in points) / len(points)
    lat = sum(point[1] for point in points) / len(points)
    return {"lon": round(lon, 4), "lat": round(lat, 4)}


def collection_center(feature_collection: dict[str, Any], feature_ids: list[str] | None = None) -> dict[str, float]:
    features = feature_collection.get("features", [])
    if feature_ids is not None:
        selected = [feature_by_id(feature_collection, feature_id) for feature_id in feature_ids]
    else:
        selected = features
    centroids = [feature_centroid(feature) for feature in selected]
    lon = sum(point["lon"] for point in centroids) / len(centroids)
    lat = sum(point["lat"] for point in centroids) / len(centroids)
    return {"lon": round(lon, 4), "lat": round(lat, 4)}


def point_in_feature(feature: dict[str, Any], lon: float, lat: float) -> bool:
    geometry = feature.get("geometry") or {}
    geometry_type = geometry.get("type")
    if geometry_type == "Polygon":
        return _point_in_ring(lon, lat, geometry["coordinates"][0])
    if geometry_type == "MultiPolygon":
        return any(_point_in_ring(lon, lat, polygon[0]) for polygon in geometry["coordinates"])
    raise ValueError("point_in_feature only supports polygonal features.")


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius_km = 6371.0
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (
        math.sin(d_lat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(d_lon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return radius_km * c


def safe_layer_id(value: str) -> str:
    return slugify(value.replace(":", "-"))


def slugify(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", value.strip().lower())
    return normalized.strip("-") or "item"


def cache_root() -> Path:
    return Path(".cache/geography").resolve()


def _flatten_geometry_points(geometry: dict[str, Any]) -> list[tuple[float, float]]:
    geometry_type = geometry.get("type")
    coordinates = geometry.get("coordinates") or []
    if geometry_type == "Point":
        return [(coordinates[0], coordinates[1])]
    if geometry_type == "LineString":
        return [(point[0], point[1]) for point in coordinates]
    if geometry_type == "Polygon":
        return [(point[0], point[1]) for point in coordinates[0]]
    if geometry_type == "MultiPolygon":
        return [(point[0], point[1]) for polygon in coordinates for point in polygon[0]]
    raise ValueError(f"Unsupported geometry type '{geometry_type}'.")


def _point_in_ring(lon: float, lat: float, ring: list[list[float]]) -> bool:
    inside = False
    j = len(ring) - 1
    for i, vertex in enumerate(ring):
        xi, yi = vertex
        xj, yj = ring[j]
        intersects = ((yi > lat) != (yj > lat)) and (lon < (xj - xi) * (lat - yi) / ((yj - yi) or 1e-9) + xi)
        if intersects:
            inside = not inside
        j = i
    return inside
